from __future__ import annotations

import calendar
import re
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

SEP = "━━━━━━━━━━━━━━━"


def _fmt(amount: float) -> str:
    return f"{amount:,.0f}".replace(",", " ").replace(".0", "")


def _pct(occupied: int, total: int) -> int:
    if total <= 0:
        return 0
    return round(occupied / total * 100)


def _profit_line(amount: float) -> str:
    if amount > 0:
        return f"🔺 +{_fmt(amount)} ₽"
    if amount < 0:
        return f"🔻 -{_fmt(abs(amount))} ₽"
    return f"{_fmt(0)} ₽"


def _clean_category(name: str) -> str:
    return re.sub(r"^[\U0001F300-\U0001FAFF\U00002600-\U000027BF\s]+", "", name).strip() or name


def _category_block(title: str, items: list[tuple[str, float]]) -> list[str]:
    if not items:
        return []
    lines = [title]
    for i, (cat, amount) in enumerate(items):
        prefix = "└" if i == len(items) - 1 else "├"
        lines.append(f"{prefix} {_clean_category(cat)} — {_fmt(amount)} ₽")
    return lines


async def build_stats_text(db: Database, year: int, month: int, today: date) -> str:
    booking_income = await db.booking_income_month(year, month)
    other_income = await db.finance_sum_month("income", year, month)
    expenses = await db.finance_sum_month("expense", year, month)
    total_income = booking_income + other_income
    net = total_income - expenses

    apartments = await db.list_apartments()
    days_in_month = calendar.monthrange(year, month)[1]
    is_current = year == today.year and month == today.month
    ref_day = today.day if is_current else days_in_month

    if apartments:
        occupied_all = 0
        for apt in apartments:
            occupied_all += await db.occupied_days_count(
                apt["id"],
                year,
                month,
                up_to_day=ref_day if is_current else None,
            )
        load_pct = _pct(occupied_all, ref_day * len(apartments))
    else:
        load_pct = 0

    lines = [
        f"📊 {MONTHS_RU[month]} {year}",
        "",
        "💰 Финансовый результат",
        f"├ Чистая прибыль: {_profit_line(net)}",
        f"├ Общий доход: {_fmt(total_income)} ₽",
        f"│  ├ Бронирования: {_fmt(booking_income)} ₽",
        f"│  └ Прочий доход: {_fmt(other_income)} ₽",
        f"└ Расходы: {_fmt(expenses)} ₽",
        "",
        "🏘 Загрузка объектов",
        f"└ Общая загрузка: {load_pct}%",
    ]

    if not apartments:
        lines.extend(["", "— объектов пока нет —"])
        return "\n".join(lines)

    for apt in apartments:
        aid = apt["id"]
        b_inc = await db.booking_income_month(year, month, aid)
        o_inc = await db.finance_sum_month("income", year, month, aid)
        exp = await db.finance_sum_month("expense", year, month, aid)
        inc = b_inc + o_inc
        profit = inc - exp
        occ = await db.occupied_days_count(
            aid, year, month, up_to_day=ref_day if is_current else None
        )
        denom = ref_day if is_current else days_in_month
        apt_pct = _pct(occ, denom)

        lines.extend(
            [
                "",
                SEP,
                f"🏠 {apt['name']}",
                "",
                "💵 Финансы",
                f"├ Прибыль: {_profit_line(profit)}",
                f"├ Доход: {_fmt(inc)} ₽",
                f"└ Расходы: {_fmt(exp)} ₽",
                "",
                "📅 Загрузка",
                f"└ {occ} / {denom} дней ({apt_pct}%)",
            ]
        )

        exp_cats = await db.finance_by_category_month("expense", year, month, aid)
        if exp_cats:
            lines.append("")
            lines.extend(_category_block("🧾 Расходы", exp_cats))

        inc_cats = await db.finance_by_category_month("income", year, month, aid)
        if inc_cats:
            lines.append("")
            lines.extend(_category_block("💎 Доп. доходы", inc_cats))

        lines.append(SEP)

    return "\n".join(lines)
