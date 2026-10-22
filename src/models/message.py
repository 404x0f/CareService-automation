"""Таблица messages: входящие webhook и ответы, отправленные нашим кодом."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy import (
    text as sql_text,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.core.base_model import Base


class MessageSource(StrEnum):
    """Кто написал сообщение: клиент, менеджер или наш бот."""

    CLIENT = 'client'
    MANAGER = 'manager'
    BOT = 'bot'


class MessageDirection(StrEnum):
    """Направление относительно нашего аккаунта Avito."""

    INCOMING = 'incoming'
    OUTGOING = 'outgoing'


class Message(Base):
    """Одна запись на уникальный Avito message ID внутри диалога."""

    __tablename__ = 'messages'

    # Внутренний UUID записи и связь с chats.id.
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    chat_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey('chats.id'), nullable=False)
    # Внешний ID защищает от повторной доставки входящего webhook.
    avito_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    # Источник уточняет автора нашей стороны, направление отделяет нас от клиента.
    source: Mapped[MessageSource] = mapped_column(String(16), nullable=False)
    direction: Mapped[MessageDirection] = mapped_column(String(16), nullable=False)
    # Текст и время события Avito либо подтверждённой отправки нами.
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # True только для сообщения, отправленного менеджером, а не ботом.
    sent_by_manager: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=sql_text('false'), nullable=False
    )

    # Даже одновременные webhook не могут вставить один Avito ID дважды.
    __table_args__ = (
        UniqueConstraint('avito_message_id', name='uq_messages_avito_message_id'),
    )
