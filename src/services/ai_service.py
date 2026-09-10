import logging
from pathlib import Path

from openai import AsyncOpenAI

from src.core.settings import settings

# Добавлено: отдельный файл для пар "сообщение клиента - ответ ИИ".
LOG_DIRECTORY = Path(__file__).resolve().parents[2] / "logs"
LOG_DIRECTORY.mkdir(exist_ok=True)

dialog_logger = logging.getLogger("ai_dialog")
dialog_logger.setLevel(logging.INFO)
dialog_logger.propagate = False

if not dialog_logger.handlers:
    dialog_handler = logging.FileHandler(
        LOG_DIRECTORY / "ai_dialog.log",
        encoding="utf-8",
    )
    dialog_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
    dialog_logger.addHandler(dialog_handler)


class AIService:

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )

    async def generate_reply(self, user_message: str) -> str:

        response = await self.client.chat.completions.create(
            model="glm-5.3-flash",
            messages=[
                {
                    "role": "system",
                    "content": """
                        Ты менеджер по продажам на Avito.

                        Отвечай клиентам естественно, коротко и вежливо.
                        Не говори, что ты искусственный интеллект.
                        Не придумывай информацию, которой нет в контексте.

                        Твоя задача — ответить на сообщение клиента.
                        """,
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ],
        )

        answer = response.choices[0].message.content

        # Добавлено: сохраняем в отдельный файл исходное сообщение и ответ.
        dialog_logger.info(
            "Сообщение пользователя: %s\nОтвет ИИ: %s\n",
            user_message,
            answer,
        )

        return answer

ai_service = AIService()
