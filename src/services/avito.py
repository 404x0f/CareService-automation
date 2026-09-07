import httpx
from fastapi import HTTPException, status

from src.core.settings import settings
from src.services.avito_auth import avito_auth


class AvitoService:

    async def _get_headers(self) -> dict[str, str]:
        token = await avito_auth.get_access_token()

        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def has_replied(self, chat_id):
        headers = await self._get_headers()

        url = (
            f"https://api.avito.ru"
            f"/messenger/v3/accounts/{settings.avito_account_id}"
            f"/chats/{chat_id}/messages/"
        )
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=headers,
            )
        
        response.raise_for_status()

        result = response.json()

        return any(
            message["direction"] == "out"
            for message in result["messages"]
        )
        

    async def read_chat(self, chat_id):
        headers = await self._get_headers()

        url = (
            f"https://api.avito.ru"
            f"/messenger/v1/accounts/{settings.avito_account_id}/"
            f"/chats/{chat_id}/read/"
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
            )

        response.raise_for_status()
        return response.json()
        
        

    async def send_messages(self):
        headers = await self._get_headers()
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

avito_service = AvitoService()