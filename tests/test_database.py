from datetime import date

import pytest

from bot.database import Database
from tests.conftest import ADMIN_ID


@pytest.mark.asyncio
class TestAccess:
    async def test_ensure_owner_once(self, tmp_path):
        database = Database(str(tmp_path / "owner.db"))
        await database.connect()
        await database.ensure_owner(1, "Owner")
        await database.ensure_owner(2, "Other")
        admins = await database.get_admins()
        assert len(admins) == 1
        assert admins[0]["user_id"] == 1
        await database.close()

    async def test_add_remove_admin(self, db: Database):
        await db.ensure_owner(1, "Owner")
        await db.add_admin(ADMIN_ID, "Admin")
        assert await db.is_admin(ADMIN_ID)
        await db.remove_admin(ADMIN_ID)
        assert not await db.is_admin(ADMIN_ID)


@pytest.mark.asyncio
class TestApartmentsAndCodes:
    async def test_door_code(self, db: Database):
        aid = await db.add_apartment("Мира", None)
        await db.update_apartment_door_code(aid, "4821")
        apt = await db.get_apartment(aid)
        assert apt["door_code"] == "4821"
        await db.update_apartment_door_code(aid, None)
        apt = await db.get_apartment(aid)
        assert apt["door_code"] is None


@pytest.mark.asyncio
class TestBookings:
    async def test_range_split(self, db: Database):
        aid = await db.add_apartment("A", None)
        dates = [date(2026, 5, 16), date(2026, 5, 17), date(2026, 5, 18)]
        await db.add_booking_range(aid, dates, 15000, per_day=False)
        booked = await db.get_booked_dates(aid, 2026, 5)
        assert len(booked) == 3
        assert all(v == 5000 for v in booked.values())

    async def test_delete_booking(self, db: Database):
        aid = await db.add_apartment("A", None)
        await db.add_booking_range(aid, [date(2026, 5, 10)], 3000, per_day=True)
        removed = await db.delete_booking_on_date(aid, date(2026, 5, 10))
        assert removed == 3000


@pytest.mark.asyncio
class TestFinance:
    async def test_finance_requires_apartment(self, db: Database):
        aid = await db.add_apartment("A", None)
        rid = await db.add_finance(
            aid, "expense", date(2026, 5, 1), 37000, "Аренда", None
        )
        row = await db.get_finance(rid)
        assert row["apartment_id"] == aid
        assert await db.finance_sum_month("expense", 2026, 5, aid) == 37000

    async def test_finance_pagination(self, db: Database):
        aid = await db.add_apartment("A", None)
        for i in range(12):
            await db.add_finance(
                aid, "income", date(2026, 5, min(i + 1, 28)), 100 + i, None, None
            )
        assert await db.count_finance_by_apartment(aid) == 12
        page1 = await db.list_finance_history_page(aid, 0, 10)
        page2 = await db.list_finance_history_page(aid, 10, 10)
        assert len(page1) == 10
        assert len(page2) == 2
