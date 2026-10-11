"""Один проход чата после первого таймера: контекст, AI, ответ."""

from datetime import datetime, timezone
from uuid import UUID

from src.core.dependencies import session_maker
from src.crud.chats import get_chat_for_update
from src.crud.messages import list_chat_messages, record_sent_message
from src.crud.reviews import create_review
from src.models.chat import Chat
from src.models.message import MessageDirection, MessageSource
from src.models.reply_review import ReplyReviewState
from src.services.ai_service import ai_service
from src.services.avito import avito_service
from src.utils.work_time import is_working_time


def _extract_avito_message_id(response: dict | None) -> str | None:
    """Return Avito response message ID without depending on one response shape."""
    if not isinstance(response, dict):
        return None
    message = response.get("message")
    message_id = message.get("id") if isinstance(message, dict) else None
    message_id = message_id or response.get("id") or response.get("message_id")
    return str(message_id) if message_id is not None else None


async def request_manager_review(
    chat_id: UUID, client_text: str, suggestion: str
) -> None:
    """Сохранить предложение AI и показать его менеджеру в Telegram."""
    from src.bot.main import send_for_review
    from src.services.manager_review import cancel_review

    async with session_maker() as session, session.begin():
        chat = await get_chat_for_update(session, chat_id)
        if chat is None or chat.answered:
            return
        review = await create_review(session, chat, suggestion)
        review_id = review.id
        avito_chat_id = chat.avito_chat_id

    try:
        await send_for_review(review_id, avito_chat_id, client_text, suggestion)
    except Exception:
        await cancel_review(review_id)
        raise


async def send_automatic_reply(chat_id: UUID, reply: str) -> None:
    """Вне рабочих часов отправить ответ без подтверждения менеджера."""
    async with session_maker() as session:
        chat = await session.get(Chat, chat_id)
        if chat is None or chat.answered:
            return
        avito_chat_id = chat.avito_chat_id

    response = await avito_service.send_message(avito_chat_id, reply)
    message_id = _extract_avito_message_id(response)
    sent_at = datetime.now(timezone.utc)

    async with session_maker() as session, session.begin():
        chat = await get_chat_for_update(session, chat_id)
        if chat is None:
            return
        review = await create_review(session, chat, reply)
        review.final_reply = reply
        review.state = ReplyReviewState.AUTO_SENT
        review.resolved_at = sent_at
        await record_sent_message(
            session, chat, message_id, reply, sent_at, MessageSource.BOT
        )


async def process_chat(chat_id: UUID) -> None:
    """Передать AI все сообщения, сохранённые к моменту запуска worker."""
    async with session_maker() as session:
        chat = await session.get(Chat, chat_id)
        if chat is None or chat.answered:
            return
        dialog = await list_chat_messages(session, chat)
        if not dialog:
            return
        client_text = "\n".join(
            message.text
            for message in dialog
            if message.direction == MessageDirection.INCOMING
        )

    # Контекст уже собран: новые входящие сообщения этот проход не изменяют.
    suggestion = await ai_service.generate_reply(user_message=client_text)
    if is_working_time():
        await request_manager_review(chat_id, client_text, suggestion)
    else:
        await send_automatic_reply(chat_id, suggestion)
