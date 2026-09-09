# import asyncio
# from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routers import main_router
# from src.bot.telegram_main import bot, dp
from src.core.settings import settings

app = FastAPI(
    title=settings.project_name,
    version="0.1.0",
    openapi_url=f"{settings.api_prefix}/openapi.json"
)

app.include_router(main_router, prefix=settings.api_prefix)


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Запускаем Telegram-бота в фоне
#     polling_task = asyncio.create_task(
#         dp.start_polling(bot)
#     )

#     print("Telegram bot started")

#     yield

#     # Останавливаем бота при остановке FastAPI
#     polling_task.cancel()

#     try:
#         await polling_task
#     except asyncio.CancelledError:
#         pass

#     await bot.session.close()

#     print("Telegram bot stopped")


# app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"message": "FastAPI Application"}
