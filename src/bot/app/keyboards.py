from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

inline_main = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='✅ Подтвердить', callback_data='accept'),
         InlineKeyboardButton(text='✏️ Изменить', callback_data='edit'),
         InlineKeyboardButton(text='❌ Отклонить', callback_data='cancel')]
    ]
)

inline_accept = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='✅ Подтвердить изменения', callback_data='accept_edit'),
         InlineKeyboardButton(text='❌ Отклонить', callback_data='cancel_edit')]
    ]
)