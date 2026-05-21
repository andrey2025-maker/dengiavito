from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from aiogram import Bot

from bot.config import Settings
from bot.database import Database
from bot.filters.access import IsAdminFilter
from bot.services.excel_delivery import send_excel_backup

router = Router()


@router.message(Command("excel"), IsAdminFilter())
async def cmd_excel(
    message: Message, db: Database, settings: Settings, bot: Bot
) -> None:
    if not message.from_user:
        return
    wait = await message.answer("⏳ Формирую Excel-резервную копию…")
    try:
        path = await send_excel_backup(
            bot, db, settings, message.from_user.id
        )
        await wait.edit_text(f"✅ Файл отправлен: <code>{path.name}</code>")
    except Exception:
        await wait.edit_text(
            "❌ Не удалось сформировать файл. Проверьте логи бота."
        )
        raise
