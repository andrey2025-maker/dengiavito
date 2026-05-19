from aiogram import Router, F, Bot
from aiogram.types import Message

from bot.config import Settings
from bot.database import Database
from bot.filters.access import IsAdminFilter
from bot.keyboards.inline import access_request_kb

router = Router()


def _user_link(user_id: int, username: str | None, full_name: str) -> str:
    if username:
        return f'<a href="tg://user?id={user_id}">@{username}</a> ({full_name})'
    return f'<a href="tg://user?id={user_id}">{full_name}</a>'


@router.message(~IsAdminFilter(), F.chat.type == "private")
async def non_admin_message(message: Message, bot: Bot, db: Database, settings: Settings) -> None:
    user = message.from_user
    if not user:
        return
    if await db.is_blocked(user.id):
        return
    await message.answer("Данный бот временно не работает")
    link = _user_link(user.id, user.username, user.full_name)
    await bot.send_message(
        settings.owner_id,
        f"Новое обращение от {link}\nID: <code>{user.id}</code>",
        reply_markup=access_request_kb(user.id),
        parse_mode="HTML",
    )
