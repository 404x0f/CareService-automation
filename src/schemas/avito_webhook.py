"""Превращает сырой JSON webhook Avito в понятное событие сообщения."""

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class AvitoMessageEvent:
    """Данные сообщения для записи входящего или отметки нашего ответа."""

    # ID Avito храним строками: они приходят как строки или числа.
    chat_id: str
    message_id: str
    author_id: str
    # Для исходящего сообщения текст может быть пустым; входящее проверит сервис.
    text: str
    # Время Avito используем для порядка входящих сообщений.
    created_at: datetime

    @classmethod
    def from_webhook(cls, body: dict) -> 'AvitoMessageEvent | None':
        """Вернуть событие сообщения или None, если webhook не подходит для обработки."""
        # Avito присылает разные события; нас интересует только payload.type=message.
        payload = body.get('payload')
        if not isinstance(payload, dict) or payload.get('type') != 'message':
            return None

        # Поле value должно быть объектом самого сообщения.
        message = payload.get('value')
        if not isinstance(message, dict):
            return None

        # Без этих трёх ID мы не сможем определить чат, дубль и направление.
        chat_id = message.get('chat_id')
        message_id = message.get('id') or message.get('message_id')
        author_id = message.get('author_id')
        if not chat_id or not message_id or author_id is None:
            return None

        # Если Avito не прислал время, сохраняем событие с текущим UTC временем.
        try:
            created_at = datetime.fromtimestamp(
                float(message.get('created', datetime.now(timezone.utc).timestamp())),
                tz=timezone.utc,
            )
        except (KeyError, TypeError, ValueError, OverflowError, OSError):
            return None

        # Текст извлекаем только из текстового content; остальные виды контента пусты.
        content = message.get('content')
        text = content.get('text') if isinstance(content, dict) else ''
        # Сервис получает уже нормализованные строки и время UTC.
        return cls(
            chat_id=str(chat_id),
            message_id=str(message_id),
            author_id=str(author_id),
            text=text.strip() if isinstance(text, str) else '',
            created_at=created_at,
        )
