from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from src.bot.app.texts import HELP_MESSAGE, START_MESSAGE
import src.bot.app.keyboards as kb

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(START_MESSAGE, parse_mode="HTML", reply_markup=kb.inline_main)

@router.message(Command('help'))
async def cmd_help(message: Message):
    await message.answer(HELP_MESSAGE, parse_mode="HTML", reply_markup=kb.inline_main)

@router.callback_query(F.data == 'edit')
async def edit(callback: CallbackQuery):
    await callback.answer('Изменить')
    await callback.message.edit_text('Потвердить изменнение?', reply_markup=kb.inline_accept)

@router.callback_query(F.data == 'accept_edit')
async def accept_edit(callback: CallbackQuery):
    await callback.answer('Сохранить изменния')
    await callback.message.edit_text('Изменения сохранены')

@router.callback_query(F.data == 'cancel_edit')
async def cancel_edit(callback: CallbackQuery):
    await callback.answer('Отклонить изменния')
    await callback.message.edit_text('Изменения отклонены')