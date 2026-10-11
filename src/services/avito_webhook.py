"""Webhook: первый входящий запускает один таймер, наш ответ закрывает чат."""

from datetime import datetime, timedelta, timezone

from httpx import HTTPError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.settings import settings
from src.crud.chats import get_or_create_chat
from src.crud.messages import insert_incoming_message
from src.schemas.avito_webhook import AvitoMessageEvent
from src.services.avito import avito_service


REPLY_WAIT = timedelta(minutes=3)


async def save_webhook_message(
    session: AsyncSession, event: AvitoMessageEvent
) -> str:
    """Записать входящее или отметить чат отвеченным по исходящему событию."""
    if event.author_id == str(settings.avito_account_id):
        # Любое сообщение с нашего аккаунта означает, что чат уже получил ответ.
        async with session.begin():
            chat = await get_or_create_chat(session, event.chat_id, None, None)
            chat.answered = True
        return "answered"

    if not event.text:
        return "ignored"

    try:
        already_replied = await avito_service.has_replied(chat_id=event.chat_id)
    except HTTPError:
        already_replied = False

    if already_replied:
        return "ignored_already_replied"

    async with session.begin():
        now = datetime.now(timezone.utc)
        # waiting_until попадает в INSERT только при создании нового чата.
        chat = await get_or_create_chat(
            session,
            event.chat_id,
            event.author_id,
            now + REPLY_WAIT,
        )
        # После ответа, запуска worker или исходных трёх минут новые входящие уже не нужны.
        if (
            chat.answered
            or chat.waiting_until is None
            or chat.created_at + REPLY_WAIT <= now
        ):
            return "ignored"

        # Следующие сообщения сохраняем для AI, но таймер не меняем.
        inserted = await insert_incoming_message(session, chat, event)
        if not inserted:
            return "duplicate"
        return "recorded"
