from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.config import Settings
from bot.database import Database
from bot.filters.access import IsAdminFilter
from bot.keyboards.reply import main_menu_keyboard, main_menu_text

router = Router()


@router.message(CommandStart(), IsAdminFilter())
async def cmd_start_admin(message: Message, db: Database) -> None:
    name = message.from_user.full_name if message.from_user else "Админ"
    await db.ensure_owner(message.from_user.id, name)
    await message.answer(
        main_menu_text(),
        reply_markup=main_menu_keyboard(),
    )
