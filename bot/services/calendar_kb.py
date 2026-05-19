from __future__ import annotations

import calendar
from datetime import date, timedelta

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ButtonStyle

MONTHS_RU = (
    "",
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
)
WEEKDAYS_RU = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")


def _in_range(d: date, start: date | None, end: date | None) -> bool:
    if not start:
        return False
    if not end:
        return d == start
    lo, hi = (start, end) if start <= end else (end, start)
    return lo <= d <= hi


def dates_in_range(start: date | None, end: date | None) -> list[date]:
    if not start:
        return []
    if not end or start == end:
        return [start]
    lo, hi = (start, end) if start <= end else (end, start)
    days = []
    cur = lo
    while cur <= hi:
        days.append(cur)
        cur += timedelta(days=1)
    return days


def build_calendar(
    *,
    apartment_id: int,
    year: int,
    month: int,
    booked: dict[str, float],
    anchor: date | None,
    end: date | None,
    single_day_mode: bool = False,
    show_pay_row: bool = True,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    prev_m, prev_y = (month - 1, year) if month > 1 else (12, year - 1)
    next_m, next_y = (month + 1, year) if month < 12 else (1, year + 1)
    rows.append(
        [
            InlineKeyboardButton(text="←", callback_data=f"cal_n:{apartment_id}:{prev_y}:{prev_m}"),
            InlineKeyboardButton(
                text=f"{MONTHS_RU[month]} {year}",
                callback_data="cal_ignore",
            ),
            InlineKeyboardButton(text="→", callback_data=f"cal_n:{apartment_id}:{next_y}:{next_m}"),
        ]
    )
    rows.append(
        [InlineKeyboardButton(text=d, callback_data="cal_ignore") for d in WEEKDAYS_RU]
    )

    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdayscalendar(year, month)
    for week in month_days:
        row_buttons: list[InlineKeyboardButton] = []
        for day in week:
            if day == 0:
                row_buttons.append(
                    InlineKeyboardButton(text=" ", callback_data="cal_ignore")
                )
                continue
            d = date(year, month, day)
            iso = d.isoformat()
            is_booked = iso in booked
            is_selected = _in_range(d, anchor, end)
            label = str(day)
            style = None
            if is_booked or is_selected:
                style = ButtonStyle.SUCCESS
            cb = f"cal_d:{apartment_id}:{iso}" if not single_day_mode or not is_booked else f"cal_del:{apartment_id}:{iso}"
            if single_day_mode and not is_booked:
                cb = f"cal_pick:{apartment_id}:{iso}"
            row_buttons.append(
                InlineKeyboardButton(text=label, callback_data=cb, style=style)
            )
        rows.append(row_buttons)

    if show_pay_row and anchor and not single_day_mode:
        selected = dates_in_range(anchor, end)
        free_selected = [d for d in selected if d.isoformat() not in booked]
        if free_selected:
            rows.append(
                [
                    InlineKeyboardButton(
                        text="💳 Оплачено",
                        callback_data=f"cal_pay:{apartment_id}",
                        style=ButtonStyle.PRIMARY,
                    )
                ]
            )
        elif anchor and anchor.isoformat() in booked:
            rows.append(
                [
                    InlineKeyboardButton(
                        text="🗑 Удалить запись",
                        callback_data=f"cal_del:{apartment_id}:{anchor.isoformat()}",
                        style=ButtonStyle.DANGER,
                    )
                ]
            )

    rows.append(
        [InlineKeyboardButton(text="🔙 Назад", callback_data="cal_back")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_finance_calendar(
    *,
    year: int,
    month: int,
    prefix: str = "fcal",
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    prev_m, prev_y = (month - 1, year) if month > 1 else (12, year - 1)
    next_m, next_y = (month + 1, year) if month < 12 else (1, year + 1)
    rows.append(
        [
            InlineKeyboardButton(text="←", callback_data=f"{prefix}_n:{prev_y}:{prev_m}"),
            InlineKeyboardButton(
                text=f"{MONTHS_RU[month]} {year}",
                callback_data="cal_ignore",
            ),
            InlineKeyboardButton(text="→", callback_data=f"{prefix}_n:{next_y}:{next_m}"),
        ]
    )
    rows.append(
        [InlineKeyboardButton(text=d, callback_data="cal_ignore") for d in WEEKDAYS_RU]
    )
    cal = calendar.Calendar(firstweekday=0)
    for week in cal.monthdayscalendar(year, month):
        row_buttons: list[InlineKeyboardButton] = []
        for day in week:
            if day == 0:
                row_buttons.append(
                    InlineKeyboardButton(text=" ", callback_data="cal_ignore")
                )
            else:
                d = date(year, month, day)
                row_buttons.append(
                    InlineKeyboardButton(
                        text=str(day),
                        callback_data=f"{prefix}_d:{d.isoformat()}",
                    )
                )
        rows.append(row_buttons)
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="fin_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def format_date_range(start: date, end: date | None) -> str:
    if not end or start == end:
        return start.strftime("%d.%m")
    lo, hi = (start, end) if start <= end else (end, start)
    return f"{lo.strftime('%d.%m')} – {hi.strftime('%d.%m')}"


def count_days(start: date, end: date | None) -> int:
    if not end or start == end:
        return 1
    lo, hi = (start, end) if start <= end else (end, start)
    return (hi - lo).days + 1
