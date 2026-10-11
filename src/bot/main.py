import asyncio
import logging
from uuid import UUID

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from src.bot.app.handlers.moderation import router as moderation_router
from src.bot.app.handlers.start import router as start_router
from src.bot.app.keyboards.moderation import approval_keyboard
from src.core.settings import settings

logger = logging.getLogger(__name__)

bot: Bot | None = None
dp = Dispatcher(storage=MemoryStorage())

dp.include_router(start_router)
dp.include_router(moderation_router)


def get_bot() -> Bot:
    """Вернуть общий Telegram Bot без создания клиента при импорте модуля."""
    global bot
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
    if bot is None:
        bot = Bot(token=settings.telegram_bot_token)
    return bot


async def send_for_moderation(
    candidate_id: int | UUID,
    chat_id: int | str,
    text: str,
    user_message: str = "",
) -> list[int] | None:
    """
    Отправляет AI-ответ в Telegram-чат модератора.
    Возвращает telegram message_id или None при ошибке.
    """
    if not settings.telegram_moderator_chat_ids:
        logger.error(
            "TELEGRAM_MODERATOR_CHAT_IDS не задан — не могу отправить на модерацию."
        )
        return None
    logger.info(
        "Сообщение пользователя: %s\nОтвет ИИ: %s\n",
        user_message,
        text
    )
    user_block = f"<b>Сообщение клиента:</b>\n{user_message}\n\n" if user_message else ""
    message_text = (
        f"💬 <b>Новый ответ на модерацию</b>\n\n"
        f'<b>Чат Avito:</b> <a href="https://www.avito.ru/profile/messenger/channel/{chat_id}">Открыть чат</a>\n\n'
        f"{user_block}"
        f"<b>Ответ AI:</b>\n{text}"
    )
    message_ids = []
    for moderator_chat_id in settings.telegram_moderator_chat_ids:
        try:
            msg = await get_bot().send_message(
                chat_id=moderator_chat_id,
                text=message_text,
                parse_mode="HTML",
                reply_markup=approval_keyboard(candidate_id),
            )

            message_ids.append(msg.message_id)
        except Exception:
            logger.exception(
                "Не удалось отправить на модерацию "
                "candidate_id=%s chat_id=%s",
                candidate_id,
                moderator_chat_id,
            )

    return message_ids


async def send_for_review(
    review_id: UUID,
    avito_chat_id: str,
    client_text: str,
    suggestion: str,
) -> list[int] | None:
    """Совместимый вход для нового worker workflow."""
    return await send_for_moderation(
        candidate_id=review_id,
        chat_id=avito_chat_id,
        text=suggestion,
        user_message=client_text,
    )


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    await dp.start_polling(get_bot())


if __name__ == "__main__":
    asyncio.run(main())
