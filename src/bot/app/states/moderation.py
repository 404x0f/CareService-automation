from aiogram.fsm.state import State, StatesGroup


class EditAnswer(StatesGroup):
    waiting_for_text = State()