from typing import Any

from fastapi import APIRouter
from sqlalchemy import select

from src.core.dependencies import SessionDep
from src.core.settings import settings
from src.models.avito import AvitoChat
from src.services.avito import send_messages

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

    # Проверяем, есть ли уже такой чат
    result = await session.execute(
        select(AvitoChat).where(
            AvitoChat.chat_id == chat_id
        )
    )

    chat = result.scalar_one_or_none()

    if chat:
        # Клиент уже писал раньше
        return {"ok": True}

    # Это первое сообщение клиента
    text = message.get("content", {}).get("text", "")

    chat = AvitoChat(
        chat_id=chat_id,
        client_id=message["author_id"],
        item_id=message["item_id"],
        first_message=text,
    )

    session.add(chat)
    await session.commit()

    print("ПЕРВОЕ СООБЩЕНИЕ КЛИЕНТА:")
    print(text)

    # Здесь дальше твоя логика
    # await send_message(...)

    return {"status": "ok"}


@router.post("/send_message")
async def send_message():
    await send_messages()

    return {"status": "ok"}
