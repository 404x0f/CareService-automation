import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import LinkPreviewOptions

from src.bot.app.handlers.moderation import router as moderation_router
from src.bot.app.handlers.start import router as start_router
from src.bot.app.keyboards.moderation import approval_keyboard
from src.bot.app.utils.text_formater import format_moderation_message
from src.core.settings import settings

logger = logging.getLogger(__name__)

bot = Bot(token=settings.telegram_bot_token)
dp = Dispatcher(storage=MemoryStorage())

dp.include_router(start_router)
dp.include_router(moderation_router)


async def send_for_moderation(
    candidate_id: int,
    chat_id: int,
    text: str,
    user_message: str = '',
) -> list[int] | None:
    """
    Отправляет AI-ответ в Telegram-чат модератора.
    Возвращает telegram message_id или None при ошибке.
    """
    if not settings.telegram_moderator_chat_ids:
        logger.error(
            'TELEGRAM_MODERATOR_CHAT_IDS не задан - не могу отправить на модерацию.'
        )
        return None

    logger.info('Сообщение пользователя: %s\nОтвет ИИ: %s\n', user_message, text)

    message_text = format_moderation_message(
        chat_id=str(chat_id),
        user_message=user_message,
        answer_text=text,
    )

    message_ids = []
    for moderator_chat_id in settings.telegram_moderator_chat_ids:
        try:
            msg = await bot.send_message(
                chat_id=moderator_chat_id,
                text=message_text,
                parse_mode='HTML',
                link_preview_options=LinkPreviewOptions(
                    is_disabled=True,
                ),
                reply_markup=approval_keyboard(candidate_id),
            )
            message_ids.append(msg.message_id)
        except Exception:
            logger.exception(
                'Не удалось отправить на модерацию candidate_id=%s chat_id=%s',
                candidate_id,
                moderator_chat_id,
            )

    return message_ids


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    )
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
