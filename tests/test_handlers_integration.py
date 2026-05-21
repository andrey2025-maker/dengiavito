from datetime import date

import pytest

from tests.conftest import (
    ADMIN_ID,
    OWNER_ID,
    STRANGER_ID,
    all_callbacks,
    last_text,
)
from tests.helpers import callback_update, make_message, message_update


async def feed(dp, bot, update):
    await dp.feed_update(bot, update)


@pytest.mark.asyncio
class TestAccess:
    async def test_stranger_rejected(self, dp, bot, session):
        await feed(dp, bot, message_update("hi", STRANGER_ID))
        stranger = [m for m in session.messages if m.chat_id == STRANGER_ID]
        assert stranger[-1].text == "Данный бот временно не работает"
        owner = [m for m in session.messages if m.chat_id == OWNER_ID]
        assert len(owner) == 1

    async def test_owner_start(self, dp, bot, session):
        await feed(dp, bot, message_update("/start", OWNER_ID))
        assert "Главное меню" in last_text(session)


@pytest.mark.asyncio
class TestStats:
    async def test_statistics_blockquote(self, dp, bot, db, session):
        aid = await db.add_apartment("Кв. 1", None)
        await db.add_finance(aid, "expense", date(2026, 5, 1), 1000, "Аренда", None)
        await feed(dp, bot, message_update("📊 Статистика", OWNER_ID))
        text = last_text(session)
        assert "blockquote expandable" in text
        assert "Кв. 1" in text

    async def test_stats_month_nav(self, dp, bot, db, session):
        await db.add_apartment("A", None)
        await feed(dp, bot, message_update("📊 Статистика", OWNER_ID))
        await feed(dp, bot, callback_update("stat:2026:4", OWNER_ID, update_id=2))
        assert session.edits[-1].parse_mode == "HTML"


@pytest.mark.asyncio
class TestFinancePerApt:
    async def test_finance_hub_and_income(self, dp, bot, db, session):
        aid = await db.add_apartment("Фин", None)
        await feed(dp, bot, message_update("➕ Добавление", OWNER_ID))
        await feed(dp, bot, callback_update(f"add:{aid}", OWNER_ID, update_id=2))
        await feed(dp, bot, callback_update(f"add_fin:{aid}", OWNER_ID, update_id=3))
        assert "Финансы" in session.edits[-1].text
        cbs = all_callbacks(session.edits[-1].reply_markup)
        assert f"fin_i:{aid}" in cbs

    async def test_history_pagination(self, dp, bot, db, session):
        aid = await db.add_apartment("Паг", None)
        for i in range(11):
            await db.add_finance(
                aid, "income", date(2026, 5, min(i + 1, 28)), 100, None, None
            )
        msg = make_message("x", OWNER_ID, message_id=50)
        await feed(
            dp,
            bot,
            callback_update(f"add_fin:{aid}", OWNER_ID, update_id=1, message=msg),
        )
        await feed(
            dp,
            bot,
            callback_update(f"fin_lst:{aid}:0", OWNER_ID, update_id=2, message=msg),
        )
        assert "Страница 1" in last_text(session)
        cbs = all_callbacks(session.edits[-1].reply_markup)
        assert any("fin_lst" in c and ":1" in c for c in cbs)


@pytest.mark.asyncio
class TestCodes:
    async def test_codes_menu(self, dp, bot, db, session):
        aid = await db.add_apartment("Ленина", None)
        await db.update_apartment_door_code(aid, "7734")
        await feed(dp, bot, message_update("🔑 Коды", OWNER_ID))
        text = last_text(session)
        assert "Коды квартир" in text
        assert "7734" in text
        assert any("code_sel" in c for c in all_callbacks(session.messages[-1].reply_markup))


@pytest.mark.asyncio
class TestBooking:
    async def test_single_booking(self, dp, bot, db, session):
        aid = await db.add_apartment("Бронь", None)
        await feed(dp, bot, callback_update(f"add_cal:{aid}", OWNER_ID, update_id=1))
        await feed(
            dp,
            bot,
            callback_update(f"cal_d:{aid}:2026-05-20", OWNER_ID, update_id=2),
        )
        await feed(
            dp, bot, callback_update(f"cal_pay:{aid}", OWNER_ID, update_id=3)
        )
        await feed(dp, bot, message_update("5000", OWNER_ID, update_id=4))
        await feed(
            dp, bot, callback_update("bok_confirm", OWNER_ID, update_id=5)
        )
        assert await db.get_booking_on_date(aid, date(2026, 5, 20)) is not None
