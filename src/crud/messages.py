"""Сохранение сообщений и чтение полного контекста чата."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.chat import Chat
from src.models.message import Message, MessageDirection, MessageSource
from src.schemas.avito_webhook import AvitoMessageEvent


async def insert_incoming_message(
    session: AsyncSession, chat: Chat, event: AvitoMessageEvent
) -> bool:
    """Записать входящее сообщение; False означает повтор его Avito ID."""
    result = await session.execute(
        insert(Message)
        .values(
            id=uuid4(),
            chat_id=chat.id,
            avito_message_id=event.message_id,
            source=MessageSource.CLIENT,
            direction=MessageDirection.INCOMING,
            text=event.text,
            created_at=event.created_at,
            sent_by_manager=False,
        )
        .on_conflict_do_nothing(index_elements=[Message.avito_message_id])
        .returning(Message.id)
    )
    return result.scalar_one_or_none() is not None


async def list_chat_messages(session: AsyncSession, chat: Chat) -> list[Message]:
    """Прочитать все сообщения чата по времени для контекста AI."""
    result = await session.execute(
        select(Message)
        .where(Message.chat_id == chat.id)
        .order_by(Message.created_at, Message.id)
    )
    return list(result.scalars())


async def record_sent_message(
    session: AsyncSession,
    chat: Chat,
    avito_message_id: str | None,
    text: str,
    created_at: datetime,
    source: MessageSource,
) -> None:
    """Сохранить отправленный через наш код ответ, если Avito вернул его ID."""
    chat.answered = True
    if avito_message_id is None:
        return
    await session.execute(
        insert(Message)
        .values(
            id=uuid4(),
            chat_id=chat.id,
            avito_message_id=avito_message_id,
            source=source,
            direction=MessageDirection.OUTGOING,
            text=text,
            created_at=created_at,
            sent_by_manager=source == MessageSource.MANAGER,
        )
        .on_conflict_do_nothing(index_elements=[Message.avito_message_id])
    )
