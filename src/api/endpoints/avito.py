import logging
from datetime import timedelta
from typing import Any

from fastapi import APIRouter
from httpx import HTTPError
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert

from src.core.dependencies import SessionDep
from src.core.settings import settings
from src.models.chat_processing import ChatPhase, ChatProcessingState, IncomingMessage
from src.services.avito import avito_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/avito",
)

DEBOUNCE_SECONDS = 1

@router.post("/webhook")
async def avito_webhook(
    data: dict[str, Any],
    session: SessionDep,
):
    logger.info("AVITO WEBHOOK RECEIVED: %s", data)
    payload = data.get("payload", {})

    if payload.get("type") != "message":
        return {"ok": True, "status": "ignored"}

    message = payload.get("value", {})

    if message.get("author_id") == settings.avito_account_id:
        return {"ok": True, "status": "ignored"}

    chat_id = message.get("chat_id")
    message_id = message.get("id") or message.get("message_id")
    user_message = (message.get("content", {}).get("text") or "").strip()

    if not chat_id or not message_id or not user_message:
        return {"ok": True, "status": "ignored"}

    chat_id = str(chat_id)
    message_id = str(message_id)

    logger.info(
        f'Chat_id = {chat_id}, User_message = {user_message}'
    )

    try:
        already_replied = await avito_service.has_replied(chat_id=chat_id)
    except HTTPError:
        already_replied = False

    if already_replied:
        return {"ok": True, "status": "ignored_already_replied"}

    debounce_until = func.now() + timedelta(seconds=DEBOUNCE_SECONDS)

    async with session.begin():
        message_result = await session.execute(
            insert(IncomingMessage)
            .values(
                avito_message_id=message_id,
                chat_id=chat_id,
                text=user_message,
            )
            .on_conflict_do_nothing(
                index_elements=[IncomingMessage.avito_message_id]
            )
            .returning(IncomingMessage.id)
        )

        if message_result.scalar_one_or_none() is None:
            return {"ok": True, "status": "duplicate"}

        await session.execute(
            insert(ChatProcessingState)
            .values(
                chat_id=chat_id,
                phase=ChatPhase.COLLECTING,
                debounce_until=debounce_until,
            )
            .on_conflict_do_update(
                index_elements=[ChatProcessingState.chat_id],
                set_={
                    "debounce_until": debounce_until,
                    "updated_at": func.now(),
                },
            )
        )

    return {"ok": True, "status": "accepted"}

