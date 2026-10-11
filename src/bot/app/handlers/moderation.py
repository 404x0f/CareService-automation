import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import update

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
from src.services.avito import avito_service

logger = logging.getLogger(__name__)

router = Router()


class EditState(StatesGroup):
    waiting_for_text = State()

@router.callback_query(F.data.startswith("approve:"))
async def handle_approve(callback: CallbackQuery) -> None:
    candidate_id = int(callback.data.split(":")[1])

    async with session_maker() as session, session.begin():
            candidate = await session.get(
                ReplyCandidate,
                candidate_id,
            )

            if candidate is None:
                await callback.answer(
                    "Кандидат не найден.",
                    show_alert=True,
                )
                return

            if candidate.status != ReplyCandidateStatus.PENDING_APPROVAL:
                await callback.answer(
                    f"Уже обработан: {candidate.status}",
                    show_alert=True,
                )
                return

            candidate.status = ReplyCandidateStatus.SENDING

            st = await session.get(
                ChatProcessingState,
                candidate.chat_id,
            )

            if st:
                st.phase = ChatPhase.SENDING

            saved_chat_id = candidate.chat_id
            saved_text = candidate.text
            saved_batch_id = candidate.batch_id

    try:
        await avito_service.send_message(
            chat_id=saved_chat_id,
            text=saved_text,
        )

    except Exception:
        logger.exception(
            "Не удалось отправить в Авито candidate_id=%s",
            candidate_id,
        )

        async with session_maker() as session, session.begin():
                candidate = await session.get(
                    ReplyCandidate,
                    candidate_id,
                )

                if candidate:
                    candidate.status = (
                        ReplyCandidateStatus.PENDING_APPROVAL
                    )

                st = await session.get(
                    ChatProcessingState,
                    saved_chat_id,
                )

                if st:
                    st.phase = ChatPhase.WAITING_APPROVAL

        await callback.answer(
            "❌ Ошибка отправки в Авито.",
            show_alert=True,
        )
        return

    async with session_maker() as session, session.begin():
            candidate = await session.get(
                ReplyCandidate,
                candidate_id,
            )

            if candidate:
                candidate.status = ReplyCandidateStatus.SENT

            await session.execute(
                update(IncomingMessage)
                .where(
                    IncomingMessage.batch_id == saved_batch_id
                )
                .values(
                    status=MessageStatus.PROCESSED
                )
            )

            await session.execute(
                update(MessageBatch)
                .where(
                    MessageBatch.id == saved_batch_id
                )
                .values(
                    status=BatchStatus.SENT
                )
            )

            st = await session.get(
                ChatProcessingState,
                saved_chat_id,
            )

            if st:
                st.phase = ChatPhase.COLLECTING
                st.active_batch_id = None
                st.lease_token = None
                st.lease_until = None
                st.debounce_until = None

    await callback.answer("✅ Отправлено в Авито!")

    try:
        await callback.message.edit_text(
            callback.message.text + "\n\n<b>✅ ОТПРАВЛЕНО</b>",
            parse_mode="HTML",
            reply_markup=None,
        )
    except Exception:
        logger.exception(
            "Не удалось обновить Telegram-сообщение"
        )

    logger.info(
        "Candidate %s одобрен и отправлен в Авито.",
        candidate_id,
    )

@router.callback_query(F.data.startswith("edit:"))
async def handle_edit(callback: CallbackQuery, state: FSMContext) -> None:
    candidate_id = int(callback.data.split(":")[1])

    async with session_maker() as session:
        candidate = await session.get(ReplyCandidate, candidate_id)

    if candidate is None:
        await callback.answer("Кандидат не найден.", show_alert=True)
        return

    if candidate.status != ReplyCandidateStatus.PENDING_APPROVAL:
        await callback.answer(
            f"Уже обработан: {candidate.status}",
            show_alert=True,
        )
        return

    await state.set_state(EditState.waiting_for_text)
    await state.update_data(
        candidate_id=candidate_id,
        original_message_id=callback.message.message_id,
    )

    await callback.answer()
    await callback.message.answer(
        f"✏️ Введите новый текст ответа для кандидата <b>#{candidate_id}</b>:\n\n"
        f"<i>Текущий текст:</i>\n{candidate.text}",
        parse_mode="HTML",
    )


@router.message(EditState.waiting_for_text)
async def handle_new_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    candidate_id: int = data["candidate_id"]
    new_text = (message.text or "").strip()

    if not new_text:
        await message.answer("Текст не может быть пустым. Попробуйте ещё раз.")
        return

    async with session_maker() as session, session.begin():
            candidate = await session.get(
                ReplyCandidate, candidate_id, with_for_update=True
            )

            if candidate is None:
                await message.answer("Кандидат не найден.")
                await state.clear()
                return

            if candidate.status != ReplyCandidateStatus.PENDING_APPROVAL:
                await message.answer(f"Уже обработан: {candidate.status}")
                await state.clear()
                return

            candidate.text = new_text

    await state.clear()
    await message.answer(
        f"✅ Текст обновлён для кандидата <b>#{candidate_id}</b>.\n\n"
        f"Нажмите <b>✅ Отправить</b> в исходном сообщении для отправки в Авито.",
        parse_mode="HTML",
    )
    logger.info("Candidate %s текст обновлён модератором.", candidate_id)


@router.callback_query(F.data.startswith("reject:"))
async def handle_reject(callback: CallbackQuery) -> None:
    candidate_id = int(callback.data.split(":")[1])

    async with session_maker() as session, session.begin():
            candidate = await session.get(
                ReplyCandidate,
                candidate_id,
            )

            if candidate is None:
                await callback.answer(
                    "Кандидат не найден.",
                    show_alert=True,
                )
                return

            if candidate.status != ReplyCandidateStatus.PENDING_APPROVAL:
                await callback.answer(
                    f"Уже обработан: {candidate.status}",
                    show_alert=True,
                )
                return

            candidate.status = ReplyCandidateStatus.REJECTED

            await session.execute(
                update(MessageBatch)
                .where(
                    MessageBatch.id == candidate.batch_id
                )
                .values(
                    status=BatchStatus.REJECTED
                )
            )

            await session.execute(
                update(IncomingMessage)
                .where(
                    IncomingMessage.batch_id == candidate.batch_id
                )
                .values(
                    status=MessageStatus.PROCESSED
                )
            )

            st = await session.get(
                ChatProcessingState,
                candidate.chat_id,
            )

            if st:
                st.phase = ChatPhase.COLLECTING
                st.active_batch_id = None
                st.lease_token = None
                st.lease_until = None
                st.debounce_until = None

    await callback.answer("❌ Отклонено.")

    try:
        await callback.message.edit_text(
            callback.message.text + "\n\n<b>❌ ОТКЛОНЕНО</b>",
            parse_mode="HTML",
            reply_markup=None,
        )
    except Exception:
        logger.exception(
            "Не удалось обновить Telegram-сообщение"
        )

    logger.info(
        "Candidate %s отклонён.",
        candidate_id,
    )
