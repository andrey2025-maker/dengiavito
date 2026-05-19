from __future__ import annotations

from datetime import date

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database import Database
from bot.filters.access import IsAdminFilter
from bot.keyboards.inline import (
    finance_categories_kb,
    finance_main_kb,
    skip_comment_kb,
)
from bot.keyboards.reply import main_menu_keyboard, main_menu_text
from bot.services.calendar_kb import build_finance_calendar
from bot.states import FinanceFlow

router = Router()


async def start_finance_with_apt(
    callback: CallbackQuery, state: FSMContext, apt_id: int, record_type: str = "income"
) -> None:
    await start_finance_flow_apt(callback, state, apt_id, record_type)


async def start_finance_flow_apt(
    callback: CallbackQuery, state: FSMContext, apt_id: int, record_type: str
) -> None:
    await state.update_data(apartment_id=apt_id, record_type=record_type)
    await state.set_state(FinanceFlow.date)
    today = date.today()
    await state.update_data(fcal_year=today.year, fcal_month=today.month)
    label = "➕ Доход" if record_type == "income" else "➖ Расход"
    await callback.message.answer(
        f"{label} — выберите дату:",
        reply_markup=build_finance_calendar(
            year=today.year, month=today.month, prefix="fcal"
        ),
    )


@router.callback_query(IsAdminFilter(), F.data == "fin_income")
async def fin_income(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(record_type="income", apartment_id=None)
    await state.set_state(FinanceFlow.date)
    today = date.today()
    await state.update_data(fcal_year=today.year, fcal_month=today.month)
    await callback.message.edit_text(
        "➕ Доход — выберите дату:",
        reply_markup=build_finance_calendar(
            year=today.year, month=today.month, prefix="fcal"
        ),
    )
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data == "fin_expense")
async def fin_expense(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(record_type="expense", apartment_id=None)
    await state.set_state(FinanceFlow.date)
    today = date.today()
    await state.update_data(fcal_year=today.year, fcal_month=today.month)
    await callback.message.edit_text(
        "➖ Расход — выберите дату:",
        reply_markup=build_finance_calendar(
            year=today.year, month=today.month, prefix="fcal"
        ),
    )
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data.startswith("fcal_n:"))
async def fcal_nav(callback: CallbackQuery, state: FSMContext) -> None:
    _, year, month = callback.data.split(":")
    await state.update_data(fcal_year=int(year), fcal_month=int(month))
    data = await state.get_data()
    kb = build_finance_calendar(
        year=int(year), month=int(month), prefix="fcal"
    )
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data.startswith("fcal_d:"))
async def fcal_pick(callback: CallbackQuery, state: FSMContext) -> None:
    iso = callback.data.split(":")[1]
    await state.update_data(record_date=iso)
    await state.set_state(FinanceFlow.amount)
    await callback.message.answer("Введите сумму (₽):")
    await callback.answer()


@router.message(IsAdminFilter(), FinanceFlow.amount)
async def fin_amount(message: Message, state: FSMContext) -> None:
    text = (message.text or "").replace(" ", "").replace("₽", "")
    try:
        amount = float(text.replace(",", "."))
    except ValueError:
        await message.answer("Введите число:")
        return
    if amount <= 0:
        await message.answer("Сумма должна быть больше 0:")
        return
    await state.update_data(amount=amount)
    await state.set_state(FinanceFlow.category)
    data = await state.get_data()
    await message.answer(
        "Выберите категорию:",
        reply_markup=finance_categories_kb(data["record_type"]),
    )


@router.callback_query(IsAdminFilter(), FinanceFlow.category, F.data.startswith("fin_cat:"))
async def fin_category(callback: CallbackQuery, state: FSMContext) -> None:
    cat = callback.data.split(":", 1)[1]
    await state.update_data(category=cat)
    await state.set_state(FinanceFlow.comment)
    await callback.message.answer(
        "Комментарий (или пропустите):",
        reply_markup=skip_comment_kb(),
    )
    await callback.answer()


@router.callback_query(IsAdminFilter(), FinanceFlow.category, F.data == "fin_cat_skip")
async def fin_category_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(category=None)
    await state.set_state(FinanceFlow.comment)
    await callback.message.answer(
        "Комментарий (или пропустите):",
        reply_markup=skip_comment_kb(),
    )
    await callback.answer()


@router.callback_query(IsAdminFilter(), FinanceFlow.comment, F.data == "fin_comment_skip")
async def fin_comment_skip(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await _save_finance(callback.message, state, db, None)
    await callback.answer("Сохранено")


@router.message(IsAdminFilter(), FinanceFlow.comment)
async def fin_comment(message: Message, state: FSMContext, db: Database) -> None:
    await _save_finance(message, state, db, (message.text or "").strip() or None)


async def _save_finance(
    message: Message, state: FSMContext, db: Database, comment: str | None
) -> None:
    data = await state.get_data()
    record_id = await db.add_finance(
        apartment_id=data.get("apartment_id"),
        record_type=data["record_type"],
        record_date=date.fromisoformat(data["record_date"]),
        amount=data["amount"],
        category=data.get("category"),
        comment=comment,
    )
    kind = "Доход" if data["record_type"] == "income" else "Расход"
    await message.answer(f"✅ {kind} сохранён (№{record_id}).")
    await state.clear()


@router.callback_query(IsAdminFilter(), F.data == "fin_cancel")
async def fin_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("💰 Финансы", reply_markup=finance_main_kb())
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data == "fin_history")
async def fin_history(callback: CallbackQuery, db: Database) -> None:
    rows = await db.list_finance_history(25)
    if not rows:
        await callback.message.answer("История пуста.")
        await callback.answer()
        return
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    lines = ["📋 История:\n"]
    builder = InlineKeyboardBuilder()
    for r in rows:
        sign = "+" if r["record_type"] == "income" else "−"
        apt = f" ({r['apt_name']})" if r["apt_name"] else ""
        cat = f" [{r['category']}]" if r["category"] else ""
        lines.append(
            f"{sign}{r['amount']:,.0f} ₽ — {r['record_date']}{apt}{cat}".replace(",", " ")
        )
        builder.button(
            text=f"🗑 {r['record_date']} {sign}{r['amount']:,.0f}".replace(",", " "),
            callback_data=f"fin_del:{r['id']}",
        )
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="fin_back"))
    await callback.message.answer(
        "\n".join(lines[:15]),
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data.startswith("fin_del:"))
async def fin_delete(callback: CallbackQuery, db: Database) -> None:
    rid = int(callback.data.split(":")[1])
    await db.delete_finance(rid)
    await callback.answer("Удалено")
    await callback.message.edit_text(callback.message.text + "\n\n🗑 Запись удалена.")


@router.callback_query(IsAdminFilter(), F.data == "fin_back")
async def fin_back(callback: CallbackQuery) -> None:
    await callback.message.edit_text("💰 Финансы", reply_markup=finance_main_kb())
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data == "fin_home")
async def fin_home(callback: CallbackQuery) -> None:
    await callback.message.answer(
        main_menu_text(),
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()
