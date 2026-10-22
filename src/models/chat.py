"""Чат Avito: один таймер и признак, что наша сторона уже ответила."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, UniqueConstraint, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.base_model import Base


class Chat(Base):
    """Одна запись на Avito chat ID."""

    __tablename__ = 'chats'

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    avito_chat_id: Mapped[str] = mapped_column(String(255), nullable=False)
    avito_user_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # После ответа нашей стороны входящие больше не обрабатываются.
    answered: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text('false'), nullable=False
    )
    # Задаётся только при создании чата первым входящим сообщением.
    # Worker обнуляет поле, когда забирает чат в работу.
    waiting_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (UniqueConstraint('avito_chat_id', name='uq_chats_avito_chat_id'),)
