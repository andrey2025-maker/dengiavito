from aiogram import Router, F
from aiogram.types import Message

from bot.database import Database
from bot.filters.access import IsAdminFilter
from bot.keyboards.inline import apartments_list_kb, finance_main_kb
from bot.keyboards.reply import main_menu_text
from bot.services.stats import build_stats_text
from bot.keyboards.inline import stats_nav_kb
from datetime import date

router = Router()


@router.message(IsAdminFilter(), F.text == "📊 Статистика")
async def menu_stats(message: Message, db: Database) -> None:
    today = date.today()
    text = await build_stats_text(db, today.year, today.month, today)
    await message.answer(
        text,
        reply_markup=stats_nav_kb(today.year, today.month),
    )


@router.message(IsAdminFilter(), F.text == "➕ Добавление")
async def menu_add(message: Message, db: Database) -> None:
    apts = await db.list_apartments()
    if not apts:
        await message.answer(
            "Сначала добавьте квартиру в разделе «⚙️ Мои квартиры»."
        )
        return
    await message.answer(
        "Выберите квартиру:",
        reply_markup=apartments_list_kb(apts, prefix="add"),
    )


@router.message(IsAdminFilter(), F.text == "💰 Финансы")
async def menu_finances(message: Message) -> None:
    await message.answer("💰 Финансы", reply_markup=finance_main_kb())
