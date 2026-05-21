import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    owner_id: int
    db_path: str = "data/bot.db"
    excel_report_time: str = "08:00"
    excel_timezone: str = "Europe/Moscow"
    excel_export_dir: str = "data/exports"


def get_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    owner_raw = os.getenv("OWNER_ID", "").strip()
    if not token or not owner_raw:
        raise RuntimeError("Задайте BOT_TOKEN и OWNER_ID в .env")
    report_time = os.getenv("EXCEL_REPORT_TIME", "08:00").strip() or "08:00"
    tz = os.getenv("EXCEL_TIMEZONE", "Europe/Moscow").strip() or "Europe/Moscow"
    export_dir = os.getenv("EXCEL_EXPORT_DIR", "data/exports").strip() or "data/exports"
    return Settings(
        bot_token=token,
        owner_id=int(owner_raw),
        excel_report_time=report_time,
        excel_timezone=tz,
        excel_export_dir=export_dir,
    )


def get_excel_zone(settings: Settings) -> ZoneInfo:
    try:
        return ZoneInfo(settings.excel_timezone)
    except Exception:
        return ZoneInfo("Europe/Moscow")
