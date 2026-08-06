from aiogram.fsm.state import State, StatesGroup


class AddErrorStates(StatesGroup):
    waiting_for_title_ru    = State()
    waiting_for_title_uz    = State()
    waiting_for_keywords    = State()
    waiting_for_solution_ru = State()
    waiting_for_solution_uz = State()


class AddVideoStates(StatesGroup):
    waiting_for_video = State()
