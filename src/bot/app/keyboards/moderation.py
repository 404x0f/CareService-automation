"""Три кнопки решения менеджера для одного reply review."""

from uuid import UUID

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def approval_keyboard(review_id: UUID) -> InlineKeyboardMarkup:
    """Собрать кнопки: отправить предложенное, изменить, отклонить."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Отправить",
                    callback_data=f"approve:{review_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"reject:{review_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Изменить",
                    callback_data=f"edit:{review_id}",
                ),
            ]
        ]
    )


review_keyboard = approval_keyboard
