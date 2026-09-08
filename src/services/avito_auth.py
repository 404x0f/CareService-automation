from datetime import datetime, timedelta, timezone

import httpx

from src.core.settings import settings


class AvitoAuth:

    def __init__(self) -> None:
        self.access_token: str | None = None
        self.expires_at: datetime | None = None

    async def get_access_token(self) -> str:
        """
        Возвращает действующий access token.

        Если токена нет или он скоро истечёт,
        получает новый.
        """

        if self._token_is_valid():
            return self.access_token

        return await self._get_new_token()

    def _token_is_valid(self) -> bool:
        if not self.access_token or not self.expires_at:
            return False

        now = datetime.now(timezone.utc)

        # Обновляем токен за 5 минут до истечения
        return now < self.expires_at - timedelta(minutes=5)

    async def _get_new_token(self) -> str:
        url = "https://api.avito.ru/token/"

        data = {
            "grant_type": "client_credentials",
            "client_id": settings.avito_client_id,
            "client_secret": settings.avito_client_secret,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                data=data,
            )

        response.raise_for_status()

        result = response.json()

        self.access_token = result["access_token"]

        self.expires_at = (
            datetime.now(timezone.utc)
            + timedelta(seconds=result["expires_in"])
        )

        return self.access_token

avito_auth = AvitoAuth()
