from __future__ import annotations

import calendar
from datetime import date

from bot.database import Database

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


def _fmt(amount: float) -> str:
    return f"{amount:,.0f}".replace(",", " ").replace(".0", "")


def _pct(occupied: int, total: int) -> int:
    if total <= 0:
        return 0
    return round(occupied / total * 100)


async def build_stats_text(db: Database, year: int, month: int, today: date) -> str:
    booking_income = await db.booking_income_month(year, month)
    other_income = await db.finance_sum_month("income", year, month)
    expenses = await db.finance_sum_month("expense", year, month)
    total_income = booking_income + other_income
    net = total_income - expenses

    apt_count = await db.apartment_count()
    days_in_month = calendar.monthrange(year, month)[1]
    ref_day = days_in_month
    if year == today.year and month == today.month:
        ref_day = today.day

    if apt_count:
        occupied_all = 0
        for apt in await db.list_apartments():
            occupied_all += await db.occupied_days_count(
                apt["id"], year, month, up_to_day=ref_day if year == today.year and month == today.month else None
            )
        total_slots = ref_day * apt_count
        load_pct = _pct(occupied_all, total_slots)
    else:
        load_pct = 0

    lines = [
        f"📊 {MONTHS_RU[month]} {year}",
        "",
        f"Чистая прибыль: {_fmt(net)} ₽",
        f"Общий доход: {_fmt(total_income)} ₽",
        f"· от броней: {_fmt(booking_income)} ₽",
        f"· прочий доход: {_fmt(other_income)} ₽",
        f"Расходы: {_fmt(expenses)} ₽",
        f"Загрузка квартир за месяц ({load_pct}%)",
        "",
        "По квартирам:",
    ]

    apartments = await db.list_apartments()
    for apt in apartments:
        aid = apt["id"]
        b_inc = await db.booking_income_month(year, month, aid)
        o_inc = await db.finance_sum_month("income", year, month, aid)
        exp = await db.finance_sum_month("expense", year, month, aid)
        inc = b_inc + o_inc
        profit = inc - exp
        occ = await db.occupied_days_count(
            aid,
            year,
            month,
            up_to_day=ref_day if year == today.year and month == today.month else None,
        )
        denom = ref_day if year == today.year and month == today.month else days_in_month
        apt_pct = _pct(occ, denom)
        lines.append(
            f"🏠 {apt['name']}: прибыль: {_fmt(profit)} ₽ "
            f"доход: {_fmt(inc)} ₽, Расходы: {_fmt(exp)} ₽ "
            f"занято {occ}/{denom} дн. ({apt_pct}%)"
        )
        exp_cats = await db.finance_by_category_month("expense", year, month, aid)
        if exp_cats:
            parts = ", ".join(f"{c}({_fmt(a)} ₽)" for c, a in exp_cats)
            lines.append(f"Расходы: {parts}")
        inc_cats = await db.finance_by_category_month("income", year, month, aid)
        if inc_cats:
            parts = ", ".join(f"{c}({_fmt(a)} ₽)" for c, a in inc_cats)
            lines.append(f"Доп. доходы: {parts}")

    if not apartments:
        lines.append("— квартир пока нет —")

    return "\n".join(lines)
