import asyncio
import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import get_settings
from bot.database import Database
from bot.handlers import setup_routers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InjectMiddleware(BaseMiddleware):
    def __init__(self, db: Database, settings: Any) -> None:
        self.db = db
        self.settings = settings

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        data["db"] = self.db
        data["settings"] = self.settings
        return await handler(event, data)


async def main() -> None:
    settings = get_settings()
    db = Database(settings.db_path)
    await db.connect()
    await db.ensure_owner(settings.owner_id, "Владелец")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(InjectMiddleware(db, settings))
    dp.include_router(setup_routers())

    try:
        logger.info("Бот запущен")
        await dp.start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
