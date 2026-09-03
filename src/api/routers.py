from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, status

from src.core.settings import settings

api_router = APIRouter(
    prefix="/api/avito",
    tags=["Avito"],
)


@api_router.post("/webhook")
async def avito_webhook(data: dict[str, Any]):
    print("Получили webhook от Avito:")

    payload = data.get("payload", {})

    if payload.get("type") != "message":
        return {"ok": True}

    message = payload.get("value", {})

    if message.get("author_id") == settings.avito_account_id:
        print("Наше сообщение, пропускаем")
        return {"ok": True}

    print(data)

    return {"status": "ok"}


@api_router.post("/send_message")
async def send_message():
    if not settings.avito_access_token or not settings.avito_test_chat_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Avito credentials are not configured",
        )

    url = (
        f"https://api.avito.ru"
        f"/messenger/v1/accounts/{settings.avito_account_id}"
        f"/chats/{settings.avito_test_chat_id}/messages"
    )

    headers = {
        "Authorization": f"Bearer {settings.avito_access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "message": {
            "text": "test",
        },
        "type": "text",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers=headers,
            json=payload,
        )

    response.raise_for_status()

    return response.json()
