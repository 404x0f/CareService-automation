
from typing import Any

from fastapi import APIRouter, BackgroundTasks

from src.core.settings import settings
from src.services.avito import avito_service

router = APIRouter(
    prefix="/api/avito",
)


@router.post("/webhook")
async def avito_webhook(
    data: dict[str, Any],
    background_tasks: BackgroundTasks,
):
    payload = data.get("payload", {})

    if payload.get("type") != "message":
        return {"ok": True}

    message = payload.get("value", {})

    if message.get("author_id") == settings.avito_account_id:
        return {"ok": True}

    chat_id = message["chat_id"]
    message_id = message.get("id") or message.get("message_id")
    user_message = message.get("content", {}).get("text")

    if not message_id or not user_message:
        return {"ok": True, "status": "ignored"}

    message_id = str(message_id)
    if not await avito_service.reserve_message(message_id):
        return {"ok": True, "status": "duplicate"}

    background_tasks.add_task(
        avito_service.generate_and_send_reply,
        message_id,
        chat_id,
        user_message,
    )
    return {"ok": True, "status": "accepted"}


@router.post("/send_message")
async def send_message():
    await avito_service.send_messages()

    return {"status": "ok"}

@router.get("/read_chat")
async def read_chats(chat_id=settings.avito_test_chat_id):
    return await avito_service.read_chat(chat_id=chat_id)

@router.get("/test")
async def test(chat_id=settings.avito_test_chat_id):
    return await avito_service.has_replied(chat_id=chat_id)
