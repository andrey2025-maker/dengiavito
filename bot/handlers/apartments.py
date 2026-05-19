from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database import Database
from bot.filters.access import IsAdminFilter
from bot.keyboards.inline import (
    add_mode_kb,
    apartment_actions_kb,
    apartments_list_kb,
    confirm_delete_kb,
)
from bot.states import ApartmentForm

router = Router()


@router.message(IsAdminFilter(), F.text == "⚙️ Мои квартиры")
async def list_apartments(message: Message, db: Database) -> None:
    apts = await db.list_apartments()
    if not apts:
        await message.answer(
            "Квартир пока нет. Нажмите «➕ Добавить квартиру».",
            reply_markup=apartments_list_kb([], add_new=True),
        )
        return
    await message.answer(
        "Ваши квартиры:",
        reply_markup=apartments_list_kb(apts, prefix="apt_view", add_new=True),
    )


@router.callback_query(IsAdminFilter(), F.data == "apt_add")
async def apt_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ApartmentForm.name)
    await state.update_data(edit_id=None)
    await callback.message.answer("Введите название квартиры:")
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data.startswith("apt_view:"))
async def apt_view(callback: CallbackQuery, db: Database) -> None:
    apt_id = int(callback.data.split(":")[1])
    apt = await db.get_apartment(apt_id)
    if not apt:
        await callback.answer("Квартира не найдена", show_alert=True)
        return
    addr = f"\nАдрес: {apt['address']}" if apt["address"] else ""
    await callback.message.edit_text(
        f"🏠 {apt['name']}{addr}",
        reply_markup=apartment_actions_kb(apt_id),
    )
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data == "apt_back")
async def apt_back(callback: CallbackQuery, db: Database) -> None:
    apts = await db.list_apartments()
    await callback.message.edit_text(
        "Ваши квартиры:",
        reply_markup=apartments_list_kb(apts, prefix="apt_view", add_new=True),
    )
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data.startswith("apt_edit:"))
async def apt_edit_start(callback: CallbackQuery, state: FSMContext) -> None:
    apt_id = int(callback.data.split(":")[1])
    await state.update_data(edit_id=apt_id)
    await state.set_state(ApartmentForm.name)
    await callback.message.answer("Новое название квартиры:")
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data.startswith("apt_del:"))
async def apt_del_ask(callback: CallbackQuery) -> None:
    apt_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "Удалить квартиру и все связанные брони и финансы?",
        reply_markup=confirm_delete_kb(apt_id),
    )
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data.startswith("apt_del_yes:"))
async def apt_del_yes(callback: CallbackQuery, db: Database) -> None:
    apt_id = int(callback.data.split(":")[1])
    await db.delete_apartment(apt_id)
    apts = await db.list_apartments()
    await callback.message.edit_text(
        "Квартира удалена.",
        reply_markup=apartments_list_kb(apts, prefix="apt_view", add_new=True),
    )
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data.startswith("apt_del_no:"))
async def apt_del_no(callback: CallbackQuery, db: Database) -> None:
    apt_id = int(callback.data.split(":")[1])
    apt = await db.get_apartment(apt_id)
    if apt:
        addr = f"\nАдрес: {apt['address']}" if apt["address"] else ""
        await callback.message.edit_text(
            f"🏠 {apt['name']}{addr}",
            reply_markup=apartment_actions_kb(apt_id),
        )
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data.startswith("apt_close:"))
async def apt_close(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    from bot.handlers.booking import open_calendar

    apt_id = int(callback.data.split(":")[1])
    await open_calendar(callback, state, apt_id, db)
    await callback.answer()


@router.message(IsAdminFilter(), ApartmentForm.name)
async def apt_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("Название не может быть пустым:")
        return
    await state.update_data(name=name)
    await state.set_state(ApartmentForm.address)
    await message.answer("Адрес (или «-» чтобы пропустить):")


@router.message(IsAdminFilter(), ApartmentForm.address)
async def apt_address(message: Message, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    name = data["name"]
    raw = (message.text or "").strip()
    address = None if raw in ("", "-", "—") else raw
    edit_id = data.get("edit_id")
    if edit_id:
        await db.update_apartment(edit_id, name, address)
        await message.answer("Квартира обновлена.")
    else:
        await db.add_apartment(name, address)
        await message.answer("Квартира добавлена.")
    await state.clear()


@router.callback_query(IsAdminFilter(), F.data.startswith("add:"))
async def add_select_apt(callback: CallbackQuery) -> None:
    apt_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "Выберите действие:",
        reply_markup=add_mode_kb(apt_id),
    )
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data == "add_back")
async def add_back(callback: CallbackQuery, db: Database) -> None:
    apts = await db.list_apartments()
    await callback.message.edit_text(
        "Выберите квартиру:",
        reply_markup=apartments_list_kb(apts, prefix="add"),
    )
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data.startswith("add_cal:"))
async def add_cal(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    from bot.handlers.booking import open_calendar

    apt_id = int(callback.data.split(":")[1])
    await open_calendar(callback, state, apt_id, db)
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data.startswith("add_fin:"))
async def add_fin(callback: CallbackQuery, state: FSMContext) -> None:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    apt_id = int(callback.data.split(":")[1])
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Доход", callback_data=f"add_fin_in:{apt_id}"
                ),
                InlineKeyboardButton(
                    text="➖ Расход", callback_data=f"add_fin_out:{apt_id}"
                ),
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"add:{apt_id}")],
        ]
    )
    await callback.message.edit_text("Выберите тип операции:", reply_markup=kb)
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data.startswith("add_fin_in:"))
async def add_fin_income(callback: CallbackQuery, state: FSMContext) -> None:
    from bot.handlers.finances import start_finance_with_apt

    apt_id = int(callback.data.split(":")[1])
    await start_finance_with_apt(callback, state, apt_id, "income")


@router.callback_query(IsAdminFilter(), F.data.startswith("add_fin_out:"))
async def add_fin_expense(callback: CallbackQuery, state: FSMContext) -> None:
    from bot.handlers.finances import start_finance_flow_apt

    apt_id = int(callback.data.split(":")[1])
    await start_finance_flow_apt(callback, state, apt_id, "expense")
