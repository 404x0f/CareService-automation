from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from src.bot.app.texts import START_MESSAGE

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        START_MESSAGE.format(
            chat_id=message.chat.id,
        ),
        parse_mode='HTML',
    )
