from aiogram.fsm.state import State, StatesGroup


class AddErrorStates(StatesGroup):
    waiting_for_title    = State()   # 1/2 — nom (istalgan tilda)
    waiting_for_solution = State()   # 2/2 — yechim (matn/video/rasm)


class AddVideoStates(StatesGroup):
    waiting_for_video = State()      # mavjud xatolikka video qo'shish
