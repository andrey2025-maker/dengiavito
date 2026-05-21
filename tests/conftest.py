from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

import pytest
from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.methods import TelegramMethod
from aiogram.methods.base import TelegramType
from aiogram.types import User

from bot.config import Settings
from bot.database import Database
from bot.handlers import setup_routers

OWNER_ID = 111_111
ADMIN_ID = 222_222
STRANGER_ID = 999_999
BLOCKED_ID = 888_888

_db_holder: dict[str, Database] = {}
_dispatcher: Dispatcher | None = None


@dataclass
class SentMessage:
    chat_id: int
    text: str
    reply_markup: Any = None
    parse_mode: str | None = None


@dataclass
class EditedMessage:
    message_id: int
    text: str
    reply_markup: Any = None
    parse_mode: str | None = None


@dataclass
class AnsweredCallback:
    text: str | None = None
    show_alert: bool = False


class MockSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[SentMessage] = []
        self.edits: list[EditedMessage] = []
        self.callback_answers: list[AnsweredCallback] = []
        self.deleted: list[int] = []

    async def close(self) -> None:
        pass

    async def stream_content(
        self,
        method: TelegramMethod[TelegramType],
        status_code: int,
        content: Any,
    ) -> AsyncGenerator[bytes, None]:
        yield b""

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramType],
        timeout: int | None = None,
    ) -> TelegramType:
        name = method.__class__.__name__
        if name == "SendMessage":
            self.messages.append(
                SentMessage(
                    chat_id=method.chat_id,
                    text=method.text,
                    reply_markup=method.reply_markup,
                    parse_mode=getattr(method, "parse_mode", None),
                )
            )
            from aiogram.types import Message as TgMessage, Chat

            return TgMessage(
                message_id=len(self.messages),
                date=0,
                chat=Chat(id=method.chat_id, type="private"),
                from_user=User(id=bot.id, is_bot=True, first_name="Bot"),
                text=method.text,
            )
        if name == "EditMessageText":
            self.edits.append(
                EditedMessage(
                    message_id=method.message_id,
                    text=method.text,
                    reply_markup=method.reply_markup,
                    parse_mode=getattr(method, "parse_mode", None),
                )
            )
            return True
        if name == "AnswerCallbackQuery":
            self.callback_answers.append(
                AnsweredCallback(
                    text=method.text,
                    show_alert=method.show_alert or False,
                )
            )
            return True
        if name == "DeleteMessage":
            self.deleted.append(method.message_id)
            return True
        return True

    def reset(self) -> None:
        self.messages.clear()
        self.edits.clear()
        self.callback_answers.clear()
        self.deleted.clear()


class DynamicInjectMiddleware(BaseMiddleware):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def __call__(self, handler, event, data):
        data["db"] = _db_holder["db"]
        data["settings"] = self.settings
        return await handler(event, data)


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings(bot_token="TEST:TOKEN", owner_id=OWNER_ID, db_path="test.db")


@pytest.fixture
async def db(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    await database.connect()
    _db_holder["db"] = database
    yield database
    await database.close()
    _db_holder.pop("db", None)


@pytest.fixture(autouse=True)
async def _autouse_db(db):
    yield


@pytest.fixture(scope="session")
def session() -> MockSession:
    return MockSession()


@pytest.fixture(autouse=True)
def _reset_session(session: MockSession):
    session.reset()
    yield


@pytest.fixture(scope="session")
def root_router():
    return setup_routers()


@pytest.fixture(scope="session")
def bot(session: MockSession) -> Bot:
    return Bot(token="123456:TEST", session=session)


@pytest.fixture
async def dp(root_router, settings: Settings) -> Dispatcher:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = Dispatcher(storage=MemoryStorage())
        _dispatcher.update.middleware(DynamicInjectMiddleware(settings))
        _dispatcher.include_router(root_router)
    return _dispatcher


def make_user(user_id: int, name: str = "User", username: str | None = None) -> User:
    return User(
        id=user_id,
        is_bot=False,
        first_name=name,
        username=username,
    )


def last_text(session: MockSession) -> str:
    if session.messages:
        return session.messages[-1].text
    if session.edits:
        return session.edits[-1].text
    return ""


def all_callbacks(markup) -> list[str]:
    if markup is None:
        return []
    result: list[str] = []
    for row in markup.inline_keyboard:
        for btn in row:
            if btn.callback_data:
                result.append(btn.callback_data)
    return result
