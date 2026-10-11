"""Создание черновика ответа и чтение решения менеджера."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.chats import get_chat_for_update
from src.models.chat import Chat
from src.models.reply_review import ReplyReview


async def create_review(
    session: AsyncSession,
    chat: Chat,
    suggested_reply: str,
) -> ReplyReview:
    """Создать предложение ответа и сразу получить его UUID для кнопки Telegram."""
    # add подходит здесь: новый review не имеет внешнего ID и не конфликтует.
    review = ReplyReview(chat_id=chat.id, suggested_reply=suggested_reply)
    session.add(review)
    # flush отправляет INSERT до конца транзакции, чтобы появился review.id.
    await session.flush()
    return review


async def get_review_for_update(
    session: AsyncSession, review_id: UUID
) -> ReplyReview | None:
    """Заблокировать конкретный review на время решения менеджера."""
    # Блокировка не позволяет двум менеджерам одновременно обработать один черновик.
    result = await session.execute(
        select(ReplyReview).where(ReplyReview.id == review_id).with_for_update()
    )
    return result.scalar_one_or_none()


async def lock_review_and_chat(
    session: AsyncSession, review_id: UUID
) -> tuple[Chat | None, ReplyReview | None]:
    """Заблокировать сначала чат, затем review, сохраняя общий порядок блокировок."""
    # Первое чтение нужно только для chat_id; review пока не изменяем.
    review = await session.get(ReplyReview, review_id)
    if review is None:
        return None, None
    # Сначала блокируем чат, затем черновик.
    chat = await get_chat_for_update(session, review.chat_id)
    review = await get_review_for_update(session, review_id)
    return chat, review
