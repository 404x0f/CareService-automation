"""Чаты: создать один раз, найти и забрать по истёкшему таймеру."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.chat import Chat


async def get_or_create_chat(
    session: AsyncSession,
    avito_chat_id: str,
    avito_user_id: str | None,
    waiting_until: datetime | None,
) -> Chat:
    """Создать чат с таймером только при первом событии и вернуть его строку."""
    await session.execute(
        insert(Chat)
        .values(
            id=uuid4(),
            avito_chat_id=avito_chat_id,
            avito_user_id=avito_user_id,
            answered=False,
            waiting_until=waiting_until,
        )
        .on_conflict_do_nothing(index_elements=[Chat.avito_chat_id])
    )
    result = await session.execute(
        select(Chat).where(Chat.avito_chat_id == avito_chat_id).with_for_update()
    )
    return result.scalar_one()


async def get_chat_for_update(session: AsyncSession, chat_id: UUID) -> Chat | None:
    """Заблокировать чат по внутреннему ID перед изменением."""
    result = await session.execute(
        select(Chat).where(Chat.id == chat_id).with_for_update()
    )
    return result.scalar_one_or_none()


async def claim_due_chats(session: AsyncSession, limit: int = 10) -> list[UUID]:
    """Забрать неотвеченные чаты, у которых закончился первый таймер."""
    result = await session.execute(
        select(Chat)
        .where(
            Chat.answered.is_(False), Chat.waiting_until <= datetime.now(timezone.utc)
        )
        .order_by(Chat.waiting_until)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    chats = list(result.scalars())
    # Обнуляем таймер: этот чат больше не попадёт в следующий проход worker.
    for chat in chats:
        chat.waiting_until = None
    return [chat.id for chat in chats]


async def schedule_retry(session: AsyncSession, chat_id: UUID) -> None:
    """После ошибки вернуть неотвеченный чат в очередь через минуту."""
    chat = await get_chat_for_update(session, chat_id)
    if chat is not None and not chat.answered:
        chat.waiting_until = datetime.now(timezone.utc) + timedelta(minutes=1)
