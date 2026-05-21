from __future__ import annotations

import calendar
import html
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


def _fmt(amount: float) -> str:
    return f"{amount:,.0f}".replace(",", " ").replace(".0", "")


def _pct(occupied: int, total: int) -> int:
    if total <= 0:
        return 0
    return round(occupied / total * 100)


def _esc(text: str) -> str:
    return html.escape(text, quote=False)


def _profit_line(amount: float) -> str:
    if amount > 0:
        return f"🔺 +{_fmt(amount)} ₽"
    if amount < 0:
        return f"🔻 -{_fmt(abs(amount))} ₽"
    return f"{_fmt(0)} ₽"


def _clean_category(name: str) -> str:
    return re.sub(r"^[\U0001F300-\U0001FAFF\U00002600-\U000027BF\s]+", "", name).strip() or name


def _category_lines(title: str, items: list[tuple[str, float]]) -> list[str]:
    if not items:
        return []
    lines = [title]
    for i, (cat, amount) in enumerate(items):
        prefix = "└" if i == len(items) - 1 else "├"
        lines.append(f"{prefix} {_esc(_clean_category(cat))} — {_fmt(amount)} ₽")
    return lines


async def _apartment_block(
    db: Database,
    apt,
    year: int,
    month: int,
    *,
    ref_day: int,
    days_in_month: int,
    is_current: bool,
) -> str:
    aid = apt["id"]
    name = _esc(apt["name"])
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

    preview = (
        f"🏠 {name}\n"
        f"Прибыль {_profit_line(profit)} · занято {occ}/{denom} ({apt_pct}%)"
    )
    body = [
        "💵 Финансы",
        f"├ Прибыль: {_profit_line(profit)}",
        f"├ Доход: {_fmt(inc)} ₽",
        f"└ Расходы: {_fmt(exp)} ₽",
        "",
        "📅 Загрузка",
        f"└ {occ} / {denom} дней ({apt_pct}%)",
    ]

    exp_cats = await db.finance_by_category_month("expense", year, month, aid)
    if exp_cats:
        body.append("")
        body.extend(_category_lines("🧾 Расходы", exp_cats))

    inc_cats = await db.finance_by_category_month("income", year, month, aid)
    if inc_cats:
        body.append("")
        body.extend(_category_lines("💎 Доп. доходы", inc_cats))

    inner = "\n".join([preview, *body])
    return f"<blockquote expandable>{inner}</blockquote>"


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

    parts = [
        f"📊 {_esc(MONTHS_RU[month])} {year}",
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
        parts.extend(["", "— объектов пока нет —"])
        return "\n".join(parts)

    parts.append("")
    parts.append("По квартирам (нажмите, чтобы раскрыть):")
    for apt in apartments:
        parts.append(
            await _apartment_block(
                db,
                apt,
                year,
                month,
                ref_day=ref_day,
                days_in_month=days_in_month,
                is_current=is_current,
            )
        )

    return "\n".join(parts)
