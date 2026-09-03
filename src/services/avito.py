import httpx
from fastapi import HTTPException, status

from src.core.settings import settings


async def send_messages():
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
