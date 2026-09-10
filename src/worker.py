"""
Worker: каждые 0.5 с захватывает чаты с истёкшим debounce,
собирает pending-сообщения в batch, генерирует ответ через AI
и отправляет его в Авито.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import session_maker
from src.models.chat_processing import (
    BatchStatus,
    ChatPhase,
    ChatProcessingState,
    IncomingMessage,
    MessageBatch,
    MessageStatus,
    ReplyCandidate,
    ReplyCandidateStatus,
)
from src.services.ai_service import ai_service
from src.services.avito import avito_service

logger = logging.getLogger(__name__)

POLL_INTERVAL = 0.5
LEASE_SECONDS = 60
RETRY_DEBOUNCE = 5.0


def _utcnow() -> datetime:
    """Naive UTC datetime — совместимо с DateTime() колонками в БД."""
    return datetime.utcnow()


async def _collect_ready_chats(session: AsyncSession) -> list[ChatProcessingState]:
    """Чаты phase=collecting с истёкшим debounce (с блокировкой строк)."""
    result = await session.execute(
        select(ChatProcessingState)
        .where(
            ChatProcessingState.phase == ChatPhase.COLLECTING,
            or_(
                ChatProcessingState.debounce_until.is_(None),
                ChatProcessingState.debounce_until <= func.now(),
            ),
        )
        .with_for_update(skip_locked=True)
    )
    return list(result.scalars().all())


async def _process_chat(chat_id: str) -> None:
    """Полный цикл обработки одного чата."""
    async with session_maker() as session:
        # 1. Захват состояния и создание batch
        async with session.begin():
            state = await session.get(
                ChatProcessingState,
                chat_id,
                with_for_update={"skip_locked": True},
            )
            if state is None:
                return
            if state.phase != ChatPhase.COLLECTING:
                return

            msgs_result = await session.execute(
                select(IncomingMessage)
                .where(
                    IncomingMessage.chat_id == chat_id,
                    IncomingMessage.status == MessageStatus.PENDING,
                )
                .order_by(IncomingMessage.received_at)
            )
            messages = list(msgs_result.scalars().all())

            if not messages:
                state.debounce_until = None
                return

            batch = MessageBatch(chat_id=chat_id, status=BatchStatus.GENERATING)
            session.add(batch)
            await session.flush()

            lease_token = str(uuid.uuid4())
            lease_until = _utcnow() + timedelta(seconds=LEASE_SECONDS)

            for msg in messages:
                msg.status = MessageStatus.PROCESSING
                msg.batch_id = batch.id

            state.phase = ChatPhase.GENERATING
            state.active_batch_id = batch.id
            state.lease_token = lease_token
            state.lease_until = lease_until

        batch_id: int = batch.id

    # 2. Генерация AI (вне транзакции)
    combined_text = "\n".join(m.text for m in messages)
    try:
        reply_text = await ai_service.generate_reply(user_message=combined_text)
    except Exception:
        logger.exception("AI упал chat_id=%s batch_id=%s", chat_id, batch_id)
        await _handle_ai_failure(chat_id, batch_id, lease_token)
        return

    # 3. Проверка рабочего времени
    from src.utils.work_time import is_working_time
    
    if not is_working_time():
        # Нерабочее время — отправляем сразу без модерации
        try:
            await avito_service.send_message(
                chat_id=chat_id,
                text=reply_text,
            )
            # Успех: помечаем batch как отправленный
            async with session_maker() as session, session.begin():
                state = await session.get(
                    ChatProcessingState, chat_id, with_for_update=True
                )
                if state is None or state.lease_token != lease_token:
                    return

                await session.execute(
                    update(IncomingMessage)
                    .where(IncomingMessage.batch_id == batch_id)
                    .values(status=MessageStatus.PROCESSED)
                )
                await session.execute(
                    update(MessageBatch)
                    .where(MessageBatch.id == batch_id)
                    .values(
                        status=BatchStatus.SENT,
                        completed_at=_utcnow(),
                    )
                )

                state.phase = ChatPhase.COLLECTING
                state.active_batch_id = None
                state.lease_token = None
                state.lease_until = None
                state.debounce_until = None

            logger.info(
                "Batch %s chat_id=%s отправлен в Авито (нерабочее время).",
                batch_id, chat_id,
            )
        except Exception:
            logger.exception(
                "Не удалось отправить в Авито (нерабочее время) chat_id=%s batch_id=%s",
                chat_id, batch_id,
            )
            await _handle_send_failure(chat_id, batch_id, lease_token)
        return

    # 4. Рабочее время: сохранить ReplyCandidate и отправить на модерацию в Telegram
    async with session_maker() as session, session.begin():
            state = await session.get(
                ChatProcessingState, chat_id, with_for_update=True
            )
            if state is None or state.lease_token != lease_token:
                return

            candidate = ReplyCandidate(
                batch_id=batch_id,
                chat_id=chat_id,
                text=reply_text,
                status=ReplyCandidateStatus.PENDING_APPROVAL,
            )
            session.add(candidate)
            await session.flush()

            state.phase = ChatPhase.WAITING_APPROVAL
            candidate_id: int = candidate.id

    # 5. Отправить в Telegram на модерацию (вне транзакции)
    from src.bot.main import send_for_moderation
    tg_message_id = await send_for_moderation(
        candidate_id=candidate_id,
        chat_id=chat_id,
        text=reply_text,
        user_message=combined_text,
    )

    if tg_message_id is not None:
        async with session_maker() as session, session.begin():
                cand = await session.get(ReplyCandidate, candidate_id)
                if cand:
                    cand.telegram_message_id = tg_message_id
        logger.info(
            "Batch %s chat_id=%s отправлен на модерацию, tg_msg=%s.",
            batch_id, chat_id, tg_message_id,
        )
    else:
        logger.error(
            "Не удалось отправить batch %s chat_id=%s в Telegram.",
            batch_id, chat_id,
        )


async def _handle_ai_failure(
    chat_id: str,
    batch_id: int,
    lease_token: str,
) -> None:
    """AI упал: batch=rejected, сообщения назад в pending, retry через 5 с."""
    async with session_maker() as session, session.begin():
            state = await session.get(
                ChatProcessingState, chat_id, with_for_update=True
            )
            if state is None or state.lease_token != lease_token:
                return

            await session.execute(
                update(IncomingMessage)
                .where(
                    IncomingMessage.batch_id == batch_id,
                    IncomingMessage.status == MessageStatus.PROCESSING,
                )
                .values(status=MessageStatus.PENDING, batch_id=None)
            )
            await session.execute(
                update(MessageBatch)
                .where(MessageBatch.id == batch_id)
                .values(status=BatchStatus.REJECTED)
            )

            state.phase = ChatPhase.COLLECTING
            state.active_batch_id = None
            state.lease_token = None
            state.lease_until = None
            state.debounce_until = _utcnow() + timedelta(seconds=RETRY_DEBOUNCE)


async def _handle_send_failure(
    chat_id: str,
    batch_id: int,
    lease_token: str,
) -> None:
    """Авито не принял ответ: фиксируем ошибку, освобождаем чат."""
    logger.error(
        "Пропускаем batch_id=%s chat_id=%s после ошибки Авито.",
        batch_id,
        chat_id,
    )
    async with session_maker() as session, session.begin():
            state = await session.get(
                ChatProcessingState, chat_id, with_for_update=True
            )
            if state is None or state.lease_token != lease_token:
                return

            await session.execute(
                update(MessageBatch)
                .where(MessageBatch.id == batch_id)
                .values(status=BatchStatus.REJECTED)
            )
            await session.execute(
                update(IncomingMessage)
                .where(
                    IncomingMessage.batch_id == batch_id,
                    IncomingMessage.status == MessageStatus.PROCESSING,
                )
                .values(status=MessageStatus.PROCESSED)
            )

            state.phase = ChatPhase.COLLECTING
            state.active_batch_id = None
            state.lease_token = None
            state.lease_until = None
            state.debounce_until = None


async def _mark_success(
    chat_id: str,
    batch_id: int,
    lease_token: str,
    messages: list[IncomingMessage],
) -> None:
    """Ответ отправлен: batch=sent, сообщения=processed, чат в collecting."""
    async with session_maker() as session, session.begin():
            state = await session.get(
                ChatProcessingState, chat_id, with_for_update=True
            )
            if state is None or state.lease_token != lease_token:
                logger.warning(
                    "Устаревший lease chat_id=%s batch_id=%s, пропускаем.",
                    chat_id, batch_id,
                )
                return

            msg_ids = [m.id for m in messages]
            await session.execute(
                update(IncomingMessage)
                .where(IncomingMessage.id.in_(msg_ids))
                .values(status=MessageStatus.PROCESSED)
            )
            await session.execute(
                update(MessageBatch)
                .where(MessageBatch.id == batch_id)
                .values(
                    status=BatchStatus.SENT,
                    completed_at=_utcnow(),
                )
            )

            state.phase = ChatPhase.COLLECTING
            state.active_batch_id = None
            state.lease_token = None
            state.lease_until = None
            state.debounce_until = None

    logger.info("Batch %s chat_id=%s успешно отправлен.", batch_id, chat_id)


async def _recover_stale_leases() -> None:
    """Восстанавливает зависшие batch (lease_until истёк)."""
    async with session_maker() as session, session.begin():
            result = await session.execute(
                select(ChatProcessingState)
                .where(
                    ChatProcessingState.phase == ChatPhase.GENERATING,
                    ChatProcessingState.lease_until <= func.now(),
                )
                .with_for_update(skip_locked=True)
            )
            stale: list[ChatProcessingState] = list(result.scalars().all())

            for state in stale:
                logger.warning(
                    "Зависший batch chat_id=%s batch_id=%s, сбрасываем.",
                    state.chat_id, state.active_batch_id,
                )
                if state.active_batch_id is not None:
                    await session.execute(
                        update(IncomingMessage)
                        .where(
                            IncomingMessage.batch_id == state.active_batch_id,
                            IncomingMessage.status == MessageStatus.PROCESSING,
                        )
                        .values(status=MessageStatus.PENDING, batch_id=None)
                    )
                    await session.execute(
                        update(MessageBatch)
                        .where(MessageBatch.id == state.active_batch_id)
                        .values(status=BatchStatus.REJECTED)
                    )

                state.phase = ChatPhase.COLLECTING
                state.active_batch_id = None
                state.lease_token = None
                state.lease_until = None
                state.debounce_until = _utcnow() + timedelta(seconds=RETRY_DEBOUNCE)



async def run_worker() -> None:
    """Основной цикл worker-а, запускается параллельно с Telegram-ботом."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("Worker запущен.")

    iteration = 0
    while True:
        try:
            if iteration % 10 == 0:
                await _recover_stale_leases()

            async with session_maker() as session, session.begin():
                    ready_chats = await _collect_ready_chats(session)

            if ready_chats:
                await asyncio.gather(
                    *[_process_chat(state.chat_id) for state in ready_chats],
                    return_exceptions=True,
                )

        except Exception:
            logger.exception("Неожиданная ошибка в основном цикле worker-а.")

        iteration += 1
        await asyncio.sleep(POLL_INTERVAL)


async def main() -> None:
    """Запускает worker и Telegram-бота параллельно."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    from src.bot.main import bot, dp
    logger.info("Запуск worker + Telegram-бот.")
    await asyncio.gather(
        run_worker(),
        dp.start_polling(bot, allowed_updates=["message", "callback_query"]),
    )


if __name__ == "__main__":
    asyncio.run(main())

