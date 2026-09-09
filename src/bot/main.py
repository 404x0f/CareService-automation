import asyncio

from aiogram import Bot, Dispatcher

from src.bot.app.handlers import router
from src.core.settings import settings

dp = Dispatcher()
bot = Bot(token=settings.telegram_bot_token)


async def main():
    dp.include_routers(router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())