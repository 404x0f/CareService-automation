"""Кнопки менеджера и ввод исправленного ответа в Telegram."""

from uuid import UUID

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from src.core.settings import settings
from src.services.manager_review import decide_review


router = Router()

# Сервис возвращает короткие статусы; менеджеру показываем понятные фразы.
RESULT_TEXT = {
    "sent": "Ответ отправлен в Avito.",
    "cancelled": "Ответ отклонён. В Avito ничего не отправлено.",
    "already_replied": "В чате уже есть ответ. Отправка отменена.",
    "send_failed": "Не удалось отправить ответ в Avito. Попробуйте ещё раз.",
    "already_handled": "Этот ответ уже обработан.",
    "not_found": "Ответ не найден.",
    "empty_reply": "Напишите непустой текст ответа.",
}


class EditingReview(StatesGroup):
    """Состояние между нажатием «Изменить» и новым текстом менеджера."""

    waiting_for_text = State()


def is_manager_chat(chat_id: int) -> bool:
    """Проверить, пришло ли действие из настроенного менеджерского чата."""
    return chat_id in settings.telegram_moderator_chat_ids


@router.callback_query()
async def review_action(callback: CallbackQuery, state: FSMContext) -> None:
    """Разобрать кнопку review: исправить, отправить или отклонить."""
    # Кнопки из других чатов не могут менять ответы клиентов.
    if callback.message is None or not is_manager_chat(callback.message.chat.id):
        await callback.answer("Этот чат не настроен для менеджеров.", show_alert=True)
        return

    # callback_data хранит действие и UUID review: например approve:<uuid>.
    try:
        action, raw_id = (callback.data or "").split(":", 1)
        review_id = UUID(raw_id)
    except ValueError:
        await callback.answer("Неверная кнопка.")
        return

    # Правка сначала ждёт текст; отправлять исходный черновик здесь нельзя.
    if action == "edit":
        await state.set_state(EditingReview.waiting_for_text)
        await state.update_data(review_id=str(review_id))
        await callback.answer()
        await callback.message.answer("Напишите новый текст ответа одним сообщением.")
        return

    # Другие действия этому обработчику не принадлежат.
    if action == "reject":
        action = "cancel"

    if action not in {"approve", "cancel"}:
        await callback.answer("Неизвестное действие.")
        return

    # Отправка/отмена и проверка актуальности выполняются в сервисе.
    result = await decide_review(review_id, action)
    await callback.answer(RESULT_TEXT.get(result, result), show_alert=result != "sent")
    # После завершённого решения удаляем кнопки, чтобы не нажать их повторно.
    if result in {"sent", "cancelled", "already_replied", "already_handled"}:
        await callback.message.edit_reply_markup(reply_markup=None)


@router.message(EditingReview.waiting_for_text)
async def edited_review(message: Message, state: FSMContext) -> None:
    """Принять исправленный текст и попросить сервис отправить именно его."""
    # Текст из другого чата не должен попасть в менеджерское решение.
    if not is_manager_chat(message.chat.id):
        await message.answer("Этот чат не настроен для менеджеров.")
        return

    # Пустую правку не отправляем в Avito и продолжаем ждать текст.
    text = (message.text or "").strip()
    if not text:
        await message.answer("Напишите непустой текст ответа.")
        return

    # FSM помнит UUID review после предыдущей кнопки «Изменить».
    data = await state.get_data()
    result = await decide_review(UUID(data["review_id"]), "edit", text)
    # После решения больше не ждём исправленный текст от этого менеджера.
    await state.clear()
    await message.answer(RESULT_TEXT.get(result, result))
