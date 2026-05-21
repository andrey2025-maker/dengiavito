from __future__ import annotations

import logging
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile

from bot.config import Settings, get_excel_zone
from bot.database import Database
from bot.services.excel_export import build_excel_backup

logger = logging.getLogger(__name__)


def _caption(settings: Settings) -> str:
    zone = get_excel_zone(settings)
    from datetime import datetime

    now = datetime.now(zone).strftime("%d.%m.%Y %H:%M")
    return f"📊 Резервная копия данных\nСформировано: {now}"


async def send_excel_backup(
    bot: Bot, db: Database, settings: Settings, chat_id: int
) -> Path:
    path = await build_excel_backup(db, settings)
    doc = FSInputFile(path, filename=path.name)
    await bot.send_document(chat_id, doc, caption=_caption(settings))
    logger.info("Excel backup sent to %s: %s", chat_id, path.name)
    return path
