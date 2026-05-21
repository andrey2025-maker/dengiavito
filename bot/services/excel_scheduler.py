from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from aiogram import Bot

from bot.config import Settings, get_excel_zone
from bot.database import Database
from bot.services.excel_delivery import send_excel_backup

logger = logging.getLogger(__name__)

MARKER_FILE = "data/.last_excel_daily"


def _parse_report_time(time_str: str) -> tuple[int, int]:
    parts = time_str.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Неверный формат EXCEL_REPORT_TIME: {time_str}")
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Неверное время: {time_str}")
    return hour, minute


def _read_last_sent_date() -> str | None:
    path = Path(MARKER_FILE)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8").strip() or None


def _write_last_sent_date(day_iso: str) -> None:
    path = Path(MARKER_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(day_iso, encoding="utf-8")


async def run_daily_excel_scheduler(
    bot: Bot, db: Database, settings: Settings
) -> None:
    try:
        target_hour, target_minute = _parse_report_time(settings.excel_report_time)
    except ValueError as e:
        logger.error("Excel scheduler disabled: %s", e)
        return

    zone = get_excel_zone(settings)
    logger.info(
        "Excel scheduler: daily at %02d:%02d (%s) → owner %s",
        target_hour,
        target_minute,
        zone,
        settings.owner_id,
    )

    while True:
        try:
            await asyncio.sleep(30)
            now = datetime.now(zone)
            if now.hour != target_hour or now.minute != target_minute:
                continue
            today = now.date().isoformat()
            if _read_last_sent_date() == today:
                continue
            await send_excel_backup(bot, db, settings, settings.owner_id)
            _write_last_sent_date(today)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Daily excel report failed")
