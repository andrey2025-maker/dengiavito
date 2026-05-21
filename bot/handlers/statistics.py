from datetime import date

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message

from bot.database import Database
from bot.filters.access import IsAdminFilter
from bot.keyboards.inline import stats_nav_kb
from bot.keyboards.reply import main_menu_keyboard, main_menu_text
from bot.services.stats import build_stats_text

router = Router()


@router.callback_query(IsAdminFilter(), F.data.startswith("stat:"))
async def stat_nav(callback: CallbackQuery, db: Database) -> None:
    _, year, month = callback.data.split(":")
    today = date.today()
    text = await build_stats_text(db, int(year), int(month), today)
    await callback.message.edit_text(
        text,
        reply_markup=stats_nav_kb(int(year), int(month)),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data == "stat_home")
async def stat_home(callback: CallbackQuery) -> None:
    await callback.message.answer(
        main_menu_text(),
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()
