from __future__ import annotations

from datetime import date

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database import Database
from bot.filters.access import IsAdminFilter
from bot.keyboards.inline import booking_confirm_kb, payment_type_kb
from bot.services.calendar_kb import (
    build_calendar,
    count_days,
    format_date_range,
    dates_in_range,
)
from bot.states import BookingFlow

router = Router()

CAL_KEY = "cal"


async def open_calendar(
    callback: CallbackQuery, state: FSMContext, apt_id: int, db: Database
) -> None:
    today = date.today()
    await state.update_data(
        apartment_id=apt_id,
        cal_year=today.year,
        cal_month=today.month,
        anchor=None,
        end=None,
        total_amount=None,
        per_day_mode=None,
    )
    await render_calendar(callback, state, db)


async def render_calendar(
    event: CallbackQuery | Message, state: FSMContext, db: Database
) -> None:
    data = await state.get_data()
    apt_id = data["apartment_id"]
    year, month = data["cal_year"], data["cal_month"]
    anchor = data.get("anchor")
    end = data.get("end")
    if anchor and isinstance(anchor, str):
        anchor = date.fromisoformat(anchor)
    if end and isinstance(end, str):
        end = date.fromisoformat(end)

    booked = await db.get_booked_dates(apt_id, year, month)
    kb = build_calendar(
        apartment_id=apt_id,
        year=year,
        month=month,
        booked=booked,
        anchor=anchor,
        end=end,
    )
    apt = await db.get_apartment(apt_id)
    title = f"📅 {apt['name'] if apt else 'Календарь'}\nВыберите даты:"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(title, reply_markup=kb)
    else:
        await event.answer(title, reply_markup=kb)


@router.callback_query(IsAdminFilter(), F.data == "cal_ignore")
async def cal_ignore(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data == "cal_back")
async def cal_back(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    from bot.keyboards.inline import add_mode_kb

    data = await state.get_data()
    apt_id = data.get("apartment_id")
    await state.clear()
    if apt_id:
        await callback.message.edit_text(
            "Выберите действие:",
            reply_markup=add_mode_kb(apt_id),
        )
    else:
        await callback.message.delete()
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data.startswith("cal_n:"))
async def cal_nav(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    _, apt_id, year, month = callback.data.split(":")
    await state.update_data(
        apartment_id=int(apt_id),
        cal_year=int(year),
        cal_month=int(month),
    )
    await render_calendar(callback, state, db)
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data.startswith("cal_d:"))
async def cal_day(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    _, apt_id, iso = callback.data.split(":", 2)
    apt_id = int(apt_id)
    clicked = date.fromisoformat(iso)
    data = await state.get_data()
    booked = await db.get_booked_dates(apt_id, clicked.year, clicked.month)
    if iso in booked:
        await state.update_data(anchor=iso, end=None)
        await render_calendar(callback, state, db)
        await callback.answer("Занятая дата — можно удалить запись")
        return

    anchor_s = data.get("anchor")
    end_s = data.get("end")
    anchor = date.fromisoformat(anchor_s) if anchor_s else None
    end = date.fromisoformat(end_s) if end_s else None

    if anchor is None:
        anchor, end = clicked, None
    elif end is None and clicked != anchor:
        end = clicked
    elif end is not None:
        anchor, end = clicked, None
    else:
        anchor, end = clicked, None

    await state.update_data(
        anchor=anchor.isoformat() if anchor else None,
        end=end.isoformat() if end else None,
    )
    await render_calendar(callback, state, db)
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data.startswith("cal_del:"))
async def cal_delete(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    _, apt_id, iso = callback.data.split(":", 2)
    apt_id = int(apt_id)
    d = date.fromisoformat(iso)
    amount = await db.delete_booking_on_date(apt_id, d)
    await callback.answer(f"Удалено: {amount:,.0f} ₽".replace(",", " "))
    await state.update_data(anchor=None, end=None)
    await render_calendar(callback, state, db)


@router.callback_query(IsAdminFilter(), F.data.startswith("cal_pay:"))
async def cal_pay(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    apt_id = data["apartment_id"]
    anchor_s, end_s = data.get("anchor"), data.get("end")
    if not anchor_s:
        await callback.answer("Сначала выберите дату", show_alert=True)
        return
    anchor = date.fromisoformat(anchor_s)
    end = date.fromisoformat(end_s) if end_s else None
    dates = dates_in_range(anchor, end)
    booked = {}
    for d in dates:
        b = await db.get_booking_on_date(apt_id, d)
        if b:
            booked[d.isoformat()] = True
    free = [d for d in dates if d.isoformat() not in booked]
    if not free:
        await callback.answer("Все выбранные даты уже заняты", show_alert=True)
        return
    await state.update_data(selected_dates=[d.isoformat() for d in free])
    if len(free) == 1:
        await state.set_state(BookingFlow.amount)
        await callback.message.answer("Введите сумму брони (₽):")
    else:
        await callback.message.answer(
            "Как указать сумму?",
            reply_markup=payment_type_kb(),
        )
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data.startswith("bok_pt:"))
async def bok_payment_type(callback: CallbackQuery, state: FSMContext) -> None:
    mode = callback.data.split(":")[1]
    await state.update_data(per_day_mode=(mode == "day"))
    await state.set_state(BookingFlow.amount)
    label = "за день" if mode == "day" else "за весь период"
    await callback.message.answer(f"Введите сумму {label} (₽):")
    await callback.answer()


@router.message(IsAdminFilter(), BookingFlow.amount)
async def bok_amount(message: Message, state: FSMContext, db: Database) -> None:
    text = (message.text or "").replace(" ", "").replace("₽", "")
    try:
        amount = float(text.replace(",", "."))
    except ValueError:
        await message.answer("Введите число:")
        return
    if amount <= 0:
        await message.answer("Сумма должна быть больше 0:")
        return
    data = await state.get_data()
    apt_id = data["apartment_id"]
    dates_iso = data.get("selected_dates") or []
    if not dates_iso and data.get("anchor"):
        anchor = date.fromisoformat(data["anchor"])
        end_s = data.get("end")
        end = date.fromisoformat(end_s) if end_s else None
        dates_iso = [d.isoformat() for d in dates_in_range(anchor, end)]

    dates = [date.fromisoformat(d) for d in dates_iso]
    per_day = data.get("per_day_mode", len(dates) == 1)
    days = len(dates)
    if per_day:
        total = amount * days
        daily = amount
    else:
        total = amount
        daily = amount / days

    apt = await db.get_apartment(apt_id)
    anchor, end = dates[0], dates[-1] if len(dates) > 1 else None
    confirm = (
        "📌 Оплачено:\n"
        f"Квартира: {apt['name'] if apt else '—'}\n"
        f"Даты: {format_date_range(anchor, end if len(dates) > 1 else None)} ({days} дн.)\n"
        f"Общая сумма: {total:,.0f} ₽\n"
        f"Стоимость суток: {daily:,.0f} ₽\n"
        "Всё верно?"
    ).replace(",", " ")
    await state.update_data(total_amount=total, per_day_mode=per_day)
    await state.set_state(BookingFlow.confirm)
    await message.answer(confirm, reply_markup=booking_confirm_kb())


@router.callback_query(IsAdminFilter(), BookingFlow.confirm, F.data == "bok_edit")
async def bok_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BookingFlow.amount)
    await callback.message.answer("Введите новую сумму (₽):")
    await callback.answer()


@router.callback_query(IsAdminFilter(), BookingFlow.confirm, F.data == "bok_cancel")
async def bok_cancel(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await state.set_state(None)
    data = await state.get_data()
    apt_id = data.get("apartment_id")
    await callback.message.answer("Отменено.")
    if apt_id:
        from datetime import date as d

        today = d.today()
        await state.update_data(
            cal_year=today.year,
            cal_month=today.month,
            anchor=None,
            end=None,
        )
        await render_calendar(callback, state, db)
    await callback.answer()


@router.callback_query(IsAdminFilter(), BookingFlow.confirm, F.data == "bok_confirm")
async def bok_confirm(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    apt_id = data["apartment_id"]
    dates = [date.fromisoformat(d) for d in data.get("selected_dates", [])]
    total = data["total_amount"]
    per_day = data.get("per_day_mode", False)
    if per_day:
        await db.add_booking_range(apt_id, dates, total / len(dates), per_day=True)
    else:
        await db.add_booking_range(apt_id, dates, total, per_day=False)
    await state.set_state(None)
    await state.update_data(anchor=None, end=None, selected_dates=None)
    await callback.message.answer("✅ Бронь сохранена.")
    await render_calendar(callback, state, db)
    await callback.answer()
