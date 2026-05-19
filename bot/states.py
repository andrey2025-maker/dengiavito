from aiogram.fsm.state import State, StatesGroup


class ApartmentForm(StatesGroup):
    name = State()
    address = State()
    confirm_delete = State()


class BookingFlow(StatesGroup):
    amount = State()
    confirm = State()


class FinanceFlow(StatesGroup):
    date = State()
    amount = State()
    category = State()
    comment = State()


class AdminAddFlow(StatesGroup):
    name = State()
