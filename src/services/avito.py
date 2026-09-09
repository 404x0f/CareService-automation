import asyncio
import logging
import time

import httpx
from fastapi import HTTPException, status

from src.core.settings import settings
from src.services.ai_service import ai_service
from src.services.avito_auth import avito_auth
from src.utils.work_time import is_working_time

logger = logging.getLogger(__name__)
PROCESSED_MESSAGE_TTL_SECONDS = 24 * 60 * 60
processed_messages: dict[str, float] = {}
processed_messages_lock = asyncio.Lock()

class AvitoService:

    async def _get_headers(self) -> dict[str, str]:
        token = await avito_auth.get_access_token()

        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def get_messeges(self, chat_id):
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

        return response.json()


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
        
        

    async def send_message(self, chat_id: str, text: str) -> dict:
        headers = await self._get_headers()

        url = (
            f"https://api.avito.ru"
            f"/messenger/v1/accounts/{settings.avito_account_id}"
            f"/chats/{chat_id}/messages"
        )

        payload = {
            "message": {
                "text": text,
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

    async def send_messages(self):
        if not settings.avito_test_chat_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Avito test chat is not configured",
            )

        return await self.send_message(settings.avito_test_chat_id, "test")


    async def reserve_message(self, message_id: str) -> bool:
        now = time.monotonic()

        async with processed_messages_lock:
            expired_before = now - PROCESSED_MESSAGE_TTL_SECONDS
            expired_ids = [
                event_id
                for event_id, received_at in processed_messages.items()
                if received_at < expired_before
            ]
            for event_id in expired_ids:
                del processed_messages[event_id]

            if message_id in processed_messages:
                return False

            processed_messages[message_id] = now
            return True


    async def release_message(self, message_id: str) -> None:
        async with processed_messages_lock:
            processed_messages.pop(message_id, None)

    async def generate_and_send_reply(
        self,
        message_id: str,
        chat_id: str,
        user_message: str,
    ) -> None:
        try:
            reply = await ai_service.generate_reply(user_message=user_message)

            # await avito_service.send_message(chat_id=chat_id, text=reply)
            # TODO: тут нужно реализовать логику с ботом
            return print(reply)
        except Exception:
            await self.release_message(message_id)
            logger.exception("Не удалось обработать сообщение Avito %s", message_id)


avito_service = AvitoService()
