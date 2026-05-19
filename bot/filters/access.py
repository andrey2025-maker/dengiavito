from typing import Any

from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from bot.config import Settings


class IsAdminFilter(BaseFilter):
    async def __call__(
        self, event: Message | CallbackQuery, db: Any, settings: Settings
    ) -> bool:
        user = event.from_user
        if not user:
            return False
        if await db.is_blocked(user.id):
            return False
        if user.id == settings.owner_id:
            await db.ensure_owner(user.id, user.full_name or "Владелец")
            return True
        return await db.is_admin(user.id)
