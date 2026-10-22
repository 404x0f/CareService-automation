"""Таблица reply_reviews: предложенный и фактически отправленный ответы."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.base_model import Base


class ReplyReviewState(StrEnum):
    """Результат проверки предложения менеджером или ночной автоотправки."""

    # Черновик ещё можно подтвердить, исправить или отменить.
    PENDING = 'pending'
    # Менеджер отправил предложенный текст без правки.
    APPROVED = 'approved'
    # Менеджер отправил свой исправленный текст.
    EDITED = 'edited'
    # Черновик отменён или устарел; ничего по нему не отправлено.
    CANCELLED = 'cancelled'
    # Ночная ветка отправила ответ без участия менеджера.
    AUTO_SENT = 'auto_sent'


class ReplyReview(Base):
    """Черновик и финальная версия одного ответа для конкретного чата."""

    __tablename__ = 'reply_reviews'

    # Внутренний UUID review передаётся в кнопках Telegram.
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    # Ответ относится к одной записи chats.
    chat_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey('chats.id'), nullable=False)
    # AI предложил этот текст; он сохраняется и после правки менеджером.
    suggested_reply: Mapped[str] = mapped_column(Text, nullable=False)
    # Фактически отправленный текст; у отменённого черновика остаётся None.
    final_reply: Mapped[str | None] = mapped_column(Text)
    # По умолчанию созданный дневной черновик ждёт менеджера.
    state: Mapped[ReplyReviewState] = mapped_column(
        String(32),
        default=ReplyReviewState.PENDING,
        server_default=ReplyReviewState.PENDING,
        nullable=False,
    )
    # UUID менеджера пока необязателен: таблицы менеджеров в текущей схеме нет.
    manager_id: Mapped[UUID | None] = mapped_column(Uuid)
    # PostgreSQL ставит время создания; решение выставляет код.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Время одобрения, правки, отмены или автоматической отправки.
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
