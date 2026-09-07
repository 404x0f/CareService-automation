from typing import Any

from fastapi import APIRouter

from src.core.dependencies import SessionDep
from src.core.settings import settings
from src.services.avito import avito_service

router = APIRouter(
    prefix="/api/avito",
)

@router.post("/webhook")
async def avito_webhook(data: dict[str, Any], 
                        session: SessionDep,):
    print("Получили webhook от Avito:")

    payload = data.get("payload", {})

    if payload.get("type") != "message":
        return {"ok": True}

    message = payload.get("value", {})

    if message.get("author_id") == settings.avito_account_id:
        return {"ok": True}

    chat_id = message["chat_id"]


    return {"status": "ok"}


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
    