import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from src.core.settings import settings

LOG_DIRECTORY = Path(__file__).resolve().parents[2] / "logs"
LOG_DIRECTORY.mkdir(exist_ok=True)

auth_logger = logging.getLogger("avito_auth")
auth_logger.setLevel(logging.INFO)
auth_logger.propagate = False

if not auth_logger.handlers:
    file_handler = logging.FileHandler(
        LOG_DIRECTORY / "avito_auth.log",
        encoding="utf-8",
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    auth_logger.addHandler(file_handler)


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
        previous_token = self.access_token
        previous_expires_at = self.expires_at
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

        if previous_token and previous_expires_at:
            expires_at = previous_expires_at.astimezone().strftime("%H:%M")
            auth_logger.info(
                "Создан новый ключ после истечения срока действия старого в %s. "
                "Старый ключ: %s. Новый ключ: %s.",
                expires_at,
                previous_token,
                self.access_token,
            )

        return self.access_token

avito_auth = AvitoAuth()
