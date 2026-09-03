from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.base_model import Base


class AvitoChat(Base):
    __tablename__ = "avito_chats"

    id: Mapped[int] = mapped_column(primary_key=True)

    chat_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )

    client_id: Mapped[int] = mapped_column(BigInteger)

    item_id: Mapped[int] = mapped_column(BigInteger)

    first_message: Mapped[str] = mapped_column(String)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )