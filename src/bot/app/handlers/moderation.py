import html
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, LinkPreviewOptions, Message
from sqlalchemy import select, update

from src.bot.app.keyboards.moderation import approval_keyboard
from src.bot.app.utils.text_formater import format_moderation_message
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
from src.crud.messages import list_chat_messages
from src.models.chat import Chat
from src.models.message import MessageDirection

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
async def handle_edit(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    candidate_id = int(callback.data.split(":")[1])

    if callback.message is None:
        await callback.answer(
            "Исходное сообщение не найдено.",
            show_alert=True,
        )
        return

    async with session_maker() as session:
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

        old_text = candidate.text

    original_message = callback.message

    await state.set_state(EditState.waiting_for_text)
    await state.update_data(
        candidate_id=candidate_id,
        original_message_id=original_message.message_id,
        original_chat_id=original_message.chat.id,
    )

    await callback.answer()

    prompt_message = await original_message.answer(
        f"✏️ Введите новый текст ответа "
        f"для кандидата <b>#{candidate_id}</b>:\n\n"
        f"<i>Текущий текст:</i>\n"
        f"{html.escape(old_text)}",
        parse_mode="HTML",
    )

    await state.update_data(
        prompt_message_id=prompt_message.message_id,
    )


@router.message(
    EditState.waiting_for_text,
    F.text,
    ~F.text.startswith("/"),
)
async def handle_new_text(
    message: Message,
    state: FSMContext,
) -> None:
    new_text = (message.text or "").strip()

    if not new_text:
        await message.answer(
            "Текст не может быть пустым. Попробуйте ещё раз."
        )
        return

    data = await state.get_data()

    candidate_id: int = data["candidate_id"]
    original_message_id: int = data["original_message_id"]
    original_chat_id: int = data["original_chat_id"]
    prompt_message_id: int = data["prompt_message_id"]
    # Проверяем кандидата и сохраняем новый текст.
    async with session_maker() as session, session.begin():
        candidate = await session.get(
            ReplyCandidate,
            candidate_id,
            with_for_update=True,
        )

        if candidate is None:
            await message.answer("Кандидат не найден.")
            await state.clear()
            return

        if candidate.status != ReplyCandidateStatus.PENDING_APPROVAL:
            await message.answer(
                f"Кандидат уже обработан: {candidate.status}"
            )
            await state.clear()
            return

        candidate.text = new_text
        batch_id = candidate.batch_id
        chat_id = candidate.chat_id

        # Получаем исходные сообщения клиента из этого batch.
        # Получаем сообщения клиента из существующей таблицы messages.
        chat_result = await session.execute(
            select(Chat).where(Chat.avito_chat_id == chat_id)
        )
        chat = chat_result.scalar_one_or_none()

        if chat is None:
            user_message = ""
            logger.warning(
                "Чат не найден: candidate_id=%s chat_id=%s",
                candidate_id,
                chat_id,
            )
        else:
            dialog = await list_chat_messages(session, chat)
            user_message = "\n".join(
                item.text
                for item in dialog
                if item.direction == MessageDirection.INCOMING
            )
    try:
        # Формируем обновлённое сообщение модерации.
        edit_message_text = format_moderation_message(
            chat_id=str(chat_id),
            user_message=user_message,
            answer_text=new_text,
            edited=True,
        )
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            logger.debug(
                "Сообщение модерации не изменилось: candidate_id=%s",
                candidate_id,
            )
        else:
            raise

    # Обновляем исходное сообщение, отключаем превью ссылки
    # и восстанавливаем кнопки модерации.
    try:
        await message.bot.edit_message_text(
            chat_id=original_chat_id,
            message_id=original_message_id,
            text=edit_message_text,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
                is_disabled=True,
            ),
            reply_markup=approval_keyboard(candidate_id),
        )
    except Exception:
        logger.exception(
            "Не удалось обновить сообщение модерации: candidate_id=%s",
            candidate_id,
        )

        await message.answer(
            "Текст сохранён в БД, но не удалось обновить "
            "исходное сообщение модерации. Проверь логи."
        )
        await state.clear()
        return

    try:
        await message.bot.delete_message(
            chat_id=original_chat_id,
            message_id=prompt_message_id,
        )
    except Exception:
        logger.exception(
            "Не удалось удалить сообщение запроса редактирования: "
            "candidate_id=%s message_id=%s",
            candidate_id,
            prompt_message_id,
        )

    await state.clear()

    await message.answer(
        f"✅ Текст кандидата <b>#{candidate_id}</b> обновлён.\n\n",
        parse_mode="HTML",
    )

    logger.info(
        "Candidate %s текст обновлён модератором.",
        candidate_id,
    )


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
