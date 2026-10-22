"""Менеджер подтверждает, исправляет или отклоняет предложение AI."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from src.core.dependencies import session_maker
from src.crud.messages import record_sent_message
from src.crud.reviews import lock_review_and_chat
from src.models.message import MessageSource
from src.models.reply_review import ReplyReviewState
from src.services.avito import avito_service
from src.services.reply_workflow import _extract_avito_message_id

logger = logging.getLogger(__name__)


async def cancel_review(review_id: UUID) -> str:
    """Отклонить черновик, ничего не отправляя в Avito."""
    async with session_maker() as session, session.begin():
        chat, review = await lock_review_and_chat(session, review_id)
        if chat is None or review is None:
            return 'not_found'
        if review.state != ReplyReviewState.PENDING:
            return 'already_handled'
        review.state = ReplyReviewState.CANCELLED
        review.resolved_at = datetime.now(timezone.utc)
    return 'cancelled'


async def send_review(review_id: UUID, edited_text: str | None = None) -> str:
    """Отправить выбранный менеджером текст и сохранить результат."""
    if edited_text is not None and not edited_text.strip():
        return 'empty_reply'

    async with session_maker() as session, session.begin():
        chat, review = await lock_review_and_chat(session, review_id)
        if chat is None or review is None:
            return 'not_found'
        if review.state != ReplyReviewState.PENDING:
            return 'already_handled'
        if chat.answered:
            return 'already_replied'

        reply = review.suggested_reply
        if edited_text is not None:
            reply = edited_text.strip()

        try:
            response = await avito_service.send_message(chat.avito_chat_id, reply)
            message_id = _extract_avito_message_id(response)
        except Exception:
            logger.exception('Could not send review %s', review_id)
            return 'send_failed'

        sent_at = datetime.now(timezone.utc)
        review.final_reply = reply
        if edited_text is None:
            review.state = ReplyReviewState.APPROVED
        else:
            review.state = ReplyReviewState.EDITED
        review.resolved_at = sent_at
        await record_sent_message(
            session, chat, message_id, reply, sent_at, MessageSource.MANAGER
        )
    return 'sent'


async def decide_review(
    review_id: UUID, action: str, edited_text: str | None = None
) -> str:
    """Выполнить действие кнопки Telegram над одним черновиком."""
    if action == 'cancel':
        return await cancel_review(review_id)
    if action == 'approve':
        return await send_review(review_id)
    if action == 'edit':
        if edited_text is None:
            return 'empty_reply'
        return await send_review(review_id, edited_text)
    return 'unknown_action'
