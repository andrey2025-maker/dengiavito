import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    owner_id: int
    db_path: str = "data/bot.db"


def get_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    owner_raw = os.getenv("OWNER_ID", "").strip()
    if not token or not owner_raw:
        raise RuntimeError("Задайте BOT_TOKEN и OWNER_ID в .env")
    return Settings(bot_token=token, owner_id=int(owner_raw))
