from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def approval_keyboard(candidate_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text='✅ Отправить',
                    callback_data=f'approve:{candidate_id}',
                ),
                InlineKeyboardButton(
                    text='❌ Отклонить',
                    callback_data=f'reject:{candidate_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    text='✏️ Изменить',
                    callback_data=f'edit:{candidate_id}',
                ),
            ],
        ]
    )
