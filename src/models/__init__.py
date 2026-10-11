"""Импорт трёх моделей регистрирует их таблицы в SQLAlchemy metadata."""

from src.models.chat import Chat
from src.models.message import Message
from src.models.reply_review import ReplyReview

__all__ = ["Chat", "Message", "ReplyReview"]
