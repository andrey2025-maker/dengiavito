from __future__ import annotations

from datetime import date

from aiogram import Bot, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.database import Database
from bot.filters.access import IsAdminFilter
from bot.keyboards.inline import finance_categories_kb, finance_hub_kb, skip_comment_kb
from bot.services.calendar_kb import build_finance_calendar
from bot.states import FinanceFlow

router = Router()

PAGE_SIZE = 10


async def finance_hub_caption(db: Database, apt_id: int) -> str:
    apt = await db.get_apartment(apt_id)
    name = apt["name"] if apt else "?"
    return f"💰 Финансы — {name}"


def _fmt_history_line(r) -> str:
    sign = "+" if r["record_type"] == "income" else "−"
    amt = f"{r['amount']:,.0f}".replace(",", " ")
    cat = f" · {r['category']}" if r["category"] else ""
    return f"• {sign}{amt} ₽ · {r['record_date']}{cat}"


def _history_keyboard(
    apt_id: int, page: int, total_pages: int, rows: list
) -> InlineKeyboardMarkup:
    ikb: list[list[InlineKeyboardButton]] = []
    for r in rows:
        sign = "+" if r["record_type"] == "income" else "−"
        amt = f"{r['amount']:,.0f}".replace(",", " ")
        btn_text = f"🗑 {r['record_date']} {sign}{amt}"[:64]
        ikb.append(
            [
                InlineKeyboardButton(
                    text=btn_text,
                    callback_data=f"fin_rm:{apt_id}:{r['id']}:{page}",
                )
            ]
        )
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text="◀", callback_data=f"fin_lst:{apt_id}:{page - 1}"
            )
        )
    if page < total_pages - 1:
        nav.append(
            InlineKeyboardButton(
                text="▶", callback_data=f"fin_lst:{apt_id}:{page + 1}"
            )
        )
    if nav:
        ikb.append(nav)
    ikb.append(
        [InlineKeyboardButton(text="🔙 К финансам", callback_data=f"fin_hub:{apt_id}")]
    )
    return InlineKeyboardMarkup(inline_keyboard=ikb)


async def render_history_panel(
    bot: Bot, chat_id: int, message_id: int, db: Database, apt_id: int, page: int
) -> None:
    total = await db.count_finance_by_apartment(apt_id)
    if total == 0:
        total_pages = 1
        page = 0
        rows = []
    else:
        total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
        page = max(0, min(page, total_pages - 1))
        offset = page * PAGE_SIZE
        rows = await db.list_finance_history_page(apt_id, offset, PAGE_SIZE)

    apt = await db.get_apartment(apt_id)
    name = apt["name"] if apt else "?"
    lines = [
        f"📋 История — {name}",
        f"Страница {page + 1} из {total_pages}",
        "",
    ]
    if not rows:
        lines.append("Записей пока нет.")
    else:
        lines.extend(_fmt_history_line(r) for r in rows)

    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text="\n".join(lines),
        reply_markup=_history_keyboard(apt_id, page, total_pages, rows),
    )


async def render_finance_hub(
    bot: Bot, chat_id: int, message_id: int, db: Database, apt_id: int
) -> None:
    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=await finance_hub_caption(db, apt_id),
        reply_markup=finance_hub_kb(apt_id),
    )


async def start_finance_flow_apt(
    callback: CallbackQuery, state: FSMContext, apt_id: int, record_type: str
) -> None:
    if not callback.message:
        return
    today = date.today()
    await state.set_state(FinanceFlow.date)
    await state.update_data(
        apartment_id=apt_id,
        record_type=record_type,
        fin_panel_mid=callback.message.message_id,
        fin_panel_cid=callback.message.chat.id,
        fcal_year=today.year,
        fcal_month=today.month,
    )
    label = "➕ Доход" if record_type == "income" else "➖ Расход"
    await callback.message.edit_text(
        f"{label} — выберите дату:",
        reply_markup=build_finance_calendar(
            year=today.year,
            month=today.month,
            apartment_id=apt_id,
        ),
    )


async def start_finance_with_apt(
    callback: CallbackQuery, state: FSMContext, apt_id: int, record_type: str = "income"
) -> None:
    await start_finance_flow_apt(callback, state, apt_id, record_type)


@router.callback_query(IsAdminFilter(), F.data.startswith("fin_i:"))
async def fin_income_apt(callback: CallbackQuery, state: FSMContext) -> None:
    apt_id = int(callback.data.split(":")[1])
    await start_finance_flow_apt(callback, state, apt_id, "income")
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data.startswith("fin_o:"))
async def fin_expense_apt(callback: CallbackQuery, state: FSMContext) -> None:
    apt_id = int(callback.data.split(":")[1])
    await start_finance_flow_apt(callback, state, apt_id, "expense")
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data.startswith("fin_hub:"))
async def fin_hub_back(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    if not callback.message:
        await callback.answer()
        return
    apt_id = int(callback.data.split(":")[1])
    await state.clear()
    await render_finance_hub(
        callback.bot, callback.message.chat.id, callback.message.message_id, db, apt_id
    )
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data.startswith("fin_lst:"))
async def fin_history_page(callback: CallbackQuery, db: Database) -> None:
    if not callback.message:
        await callback.answer()
        return
    _, aid, page_s = callback.data.split(":", 2)
    apt_id, page = int(aid), int(page_s)
    await render_history_panel(
        callback.bot,
        callback.message.chat.id,
        callback.message.message_id,
        db,
        apt_id,
        page,
    )
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data.startswith("fin_rm:"))
async def fin_delete_row(callback: CallbackQuery, db: Database) -> None:
    if not callback.message:
        await callback.answer()
        return
    parts = callback.data.split(":")
    _, apt_id_s, rid_s, page_s = parts[0], parts[1], parts[2], parts[3]
    apt_id, rid, page = int(apt_id_s), int(rid_s), int(page_s)
    row = await db.get_finance(rid)
    if not row or row["apartment_id"] != apt_id:
        await callback.answer("Запись не найдена", show_alert=True)
        return
    await db.delete_finance(rid)
    total = await db.count_finance_by_apartment(apt_id)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE) if total else 1
    new_page = min(page, total_pages - 1)
    await render_history_panel(
        callback.bot,
        callback.message.chat.id,
        callback.message.message_id,
        db,
        apt_id,
        new_page,
    )
    await callback.answer("Удалено")


@router.callback_query(IsAdminFilter(), F.data.startswith("fin_can:"))
async def fin_cancel_calendar(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    if not callback.message:
        await callback.answer()
        return
    apt_id = int(callback.data.split(":")[1])
    await state.clear()
    await render_finance_hub(
        callback.bot, callback.message.chat.id, callback.message.message_id, db, apt_id
    )
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data == "fcal_ignore")
async def fcal_ignore(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data.startswith("fcal_n:"))
async def fcal_nav(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.message:
        await callback.answer()
        return
    _, apt_s, y_s, m_s = callback.data.split(":", 3)
    apt_id, y, m = int(apt_s), int(y_s), int(m_s)
    await state.update_data(
        apartment_id=apt_id,
        fcal_year=y,
        fcal_month=m,
        fin_panel_mid=callback.message.message_id,
        fin_panel_cid=callback.message.chat.id,
    )
    kb = build_finance_calendar(year=y, month=m, apartment_id=apt_id)
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data.startswith("fcal_d:"))
async def fcal_pick(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.message:
        await callback.answer()
        return
    _, apt_s, iso = callback.data.split(":", 2)
    apt_id = int(apt_s)
    await state.update_data(
        apartment_id=apt_id,
        record_date=iso,
        fin_panel_mid=callback.message.message_id,
        fin_panel_cid=callback.message.chat.id,
    )
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
    apt_id = data.get("apartment_id")
    if not isinstance(apt_id, int):
        await message.answer("Ошибка: квартира не выбрана. Откройте «➕ Добавление» → квартира → «💰 Финансы».")
        await state.clear()
        return

    record_id = await db.add_finance(
        apartment_id=apt_id,
        record_type=data["record_type"],
        record_date=date.fromisoformat(data["record_date"]),
        amount=data["amount"],
        category=data.get("category"),
        comment=comment,
    )
    kind = "Доход" if data["record_type"] == "income" else "Расход"
    panel_mid = data.get("fin_panel_mid")
    panel_cid = data.get("fin_panel_cid")
    await state.clear()

    if panel_mid is not None and panel_cid is not None:
        try:
            await render_finance_hub(message.bot, panel_cid, panel_mid, db, apt_id)
        except Exception:
            pass

    await message.answer(f"✅ {kind} сохранён (№{record_id}).")
