from datetime import datetime
from enum import StrEnum

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.base_model import Base


class MessageStatus(StrEnum):
    PENDING = 'pending'
    PROCESSING = 'processing'
    PROCESSED = 'processed'


class ChatPhase(StrEnum):
    COLLECTING = 'collecting'
    GENERATING = 'generating'
    WAITING_APPROVAL = 'waiting_approval'
    SENDING = 'sending'


class BatchStatus(StrEnum):
    GENERATING = 'generating'
    WAITING_APPROVAL = 'waiting_approval'
    SENT = 'sent'
    REJECTED = 'rejected'


class ReplyCandidateStatus(StrEnum):
    PENDING_APPROVAL = 'pending_approval'
    SENDING = 'sending'
    SENT = 'sent'
    REJECTED = 'rejected'


class IncomingMessage(Base):
    __tablename__ = 'incoming_messages'

    id: Mapped[int] = mapped_column(primary_key=True)

    avito_message_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )

    chat_id: Mapped[str] = mapped_column(
        String(255),
        index=True,
    )

    text: Mapped[str] = mapped_column(
        Text,
    )

    status: Mapped[MessageStatus] = mapped_column(
        default=MessageStatus.PENDING,
    )

    batch_id: Mapped[int | None] = mapped_column(
        ForeignKey('message_batches.id'),
        nullable=True,
        index=True,
    )

    received_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
    )


class ChatProcessingState(Base):
    __tablename__ = 'chat_processing_states'

    chat_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )

    phase: Mapped[ChatPhase] = mapped_column(
        default=ChatPhase.COLLECTING,
    )

    debounce_until: Mapped[datetime | None]

    active_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey('message_batches.id'),
        nullable=True,
    )

    lease_until: Mapped[datetime | None]
    lease_token: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )


class MessageBatch(Base):
    __tablename__ = 'message_batches'

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    chat_id: Mapped[str] = mapped_column(
        String(255),
        index=True,
    )

    status: Mapped[BatchStatus] = mapped_column(
        default=BatchStatus.GENERATING,
    )

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
    )

    completed_at: Mapped[datetime | None]


class ReplyCandidate(Base):
    __tablename__ = 'reply_candidates'

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    batch_id: Mapped[int] = mapped_column(
        ForeignKey('message_batches.id'),
        unique=True,
    )

    chat_id: Mapped[str] = mapped_column(
        String(255),
        index=True,
    )

    text: Mapped[str] = mapped_column(
        Text,
    )

    status: Mapped[ReplyCandidateStatus] = mapped_column(
        default=ReplyCandidateStatus.PENDING_APPROVAL,
    )

    telegram_message_id: Mapped[int | None]

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
    )
