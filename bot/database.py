from __future__ import annotations

import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS admins (
    user_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    is_owner INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS blocked_users (
    user_id INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS apartments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    apartment_id INTEGER NOT NULL,
    booking_date TEXT NOT NULL,
    amount_per_day REAL NOT NULL,
    group_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(apartment_id, booking_date),
    FOREIGN KEY (apartment_id) REFERENCES apartments(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS finance_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    apartment_id INTEGER,
    record_type TEXT NOT NULL,
    record_date TEXT NOT NULL,
    amount REAL NOT NULL,
    category TEXT,
    comment TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (apartment_id) REFERENCES apartments(id) ON DELETE CASCADE
);
"""


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()

    @property
    def conn(self) -> aiosqlite.Connection:
        assert self._conn is not None
        return self._conn

    async def ensure_owner(self, user_id: int, name: str) -> None:
        row = await self.fetchone("SELECT 1 FROM admins WHERE is_owner = 1")
        if row:
            return
        await self.execute(
            "INSERT OR IGNORE INTO admins (user_id, name, is_owner, created_at) VALUES (?, ?, 1, ?)",
            (user_id, name, datetime.utcnow().isoformat()),
        )

    async def execute(self, sql: str, params: tuple = ()) -> None:
        await self.conn.execute(sql, params)
        await self.conn.commit()

    async def fetchone(self, sql: str, params: tuple = ()) -> aiosqlite.Row | None:
        cur = await self.conn.execute(sql, params)
        return await cur.fetchone()

    async def fetchall(self, sql: str, params: tuple = ()) -> list[aiosqlite.Row]:
        cur = await self.conn.execute(sql, params)
        return await cur.fetchall()

    # --- access ---
    async def is_blocked(self, user_id: int) -> bool:
        row = await self.fetchone(
            "SELECT 1 FROM blocked_users WHERE user_id = ?", (user_id,)
        )
        return row is not None

    async def is_admin(self, user_id: int) -> bool:
        row = await self.fetchone(
            "SELECT 1 FROM admins WHERE user_id = ?", (user_id,)
        )
        return row is not None

    async def block_user(self, user_id: int) -> None:
        await self.execute(
            "INSERT OR IGNORE INTO blocked_users (user_id) VALUES (?)", (user_id,)
        )

    async def add_admin(self, user_id: int, name: str) -> None:
        await self.execute(
            "INSERT OR REPLACE INTO admins (user_id, name, is_owner, created_at) VALUES (?, ?, 0, ?)",
            (user_id, name, datetime.utcnow().isoformat()),
        )

    async def remove_admin(self, user_id: int) -> None:
        await self.execute(
            "DELETE FROM admins WHERE user_id = ? AND is_owner = 0", (user_id,)
        )

    async def get_admins(self) -> list[aiosqlite.Row]:
        return await self.fetchall(
            "SELECT user_id, name, is_owner FROM admins ORDER BY is_owner DESC, name"
        )

    async def get_admin(self, user_id: int) -> aiosqlite.Row | None:
        return await self.fetchone(
            "SELECT user_id, name, is_owner FROM admins WHERE user_id = ?", (user_id,)
        )

    # --- apartments ---
    async def list_apartments(self) -> list[aiosqlite.Row]:
        return await self.fetchall(
            "SELECT id, name, address FROM apartments ORDER BY name"
        )

    async def get_apartment(self, apt_id: int) -> aiosqlite.Row | None:
        return await self.fetchone(
            "SELECT id, name, address FROM apartments WHERE id = ?", (apt_id,)
        )

    async def add_apartment(self, name: str, address: str | None) -> int:
        cur = await self.conn.execute(
            "INSERT INTO apartments (name, address, created_at) VALUES (?, ?, ?)",
            (name, address, datetime.utcnow().isoformat()),
        )
        await self.conn.commit()
        return cur.lastrowid

    async def update_apartment(
        self, apt_id: int, name: str, address: str | None
    ) -> None:
        await self.execute(
            "UPDATE apartments SET name = ?, address = ? WHERE id = ?",
            (name, address, apt_id),
        )

    async def delete_apartment(self, apt_id: int) -> None:
        await self.execute("DELETE FROM finance_records WHERE apartment_id = ?", (apt_id,))
        await self.execute("DELETE FROM bookings WHERE apartment_id = ?", (apt_id,))
        await self.execute("DELETE FROM apartments WHERE id = ?", (apt_id,))

    # --- bookings ---
    async def get_booked_dates(
        self, apartment_id: int, year: int, month: int
    ) -> dict[str, float]:
        prefix = f"{year:04d}-{month:02d}"
        rows = await self.fetchall(
            """SELECT booking_date, amount_per_day FROM bookings
               WHERE apartment_id = ? AND booking_date LIKE ?""",
            (apartment_id, f"{prefix}%"),
        )
        return {r["booking_date"]: r["amount_per_day"] for r in rows}

    async def get_booking_on_date(
        self, apartment_id: int, d: date
    ) -> aiosqlite.Row | None:
        return await self.fetchone(
            """SELECT id, amount_per_day, group_id FROM bookings
               WHERE apartment_id = ? AND booking_date = ?""",
            (apartment_id, d.isoformat()),
        )

    async def add_booking_range(
        self,
        apartment_id: int,
        dates: list[date],
        total_amount: float,
        per_day: bool,
    ) -> str:
        group_id = str(uuid.uuid4())
        if not dates:
            return group_id
        if per_day:
            amount_each = total_amount
        else:
            amount_each = total_amount / len(dates)
        now = datetime.utcnow().isoformat()
        for d in sorted(dates):
            await self.conn.execute(
                """INSERT INTO bookings
                   (apartment_id, booking_date, amount_per_day, group_id, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (apartment_id, d.isoformat(), amount_each, group_id, now),
            )
        await self.conn.commit()
        return group_id

    async def delete_booking_on_date(self, apartment_id: int, d: date) -> float:
        row = await self.get_booking_on_date(apartment_id, d)
        if not row:
            return 0.0
        amount = row["amount_per_day"]
        await self.execute(
            "DELETE FROM bookings WHERE apartment_id = ? AND booking_date = ?",
            (apartment_id, d.isoformat()),
        )
        return amount

    async def delete_booking_range(
        self, apartment_id: int, dates: list[date]
    ) -> float:
        total = 0.0
        for d in dates:
            total += await self.delete_booking_on_date(apartment_id, d)
        return total

    async def booking_income_month(
        self, year: int, month: int, apartment_id: int | None = None
    ) -> float:
        prefix = f"{year:04d}-{month:02d}"
        if apartment_id:
            row = await self.fetchone(
                """SELECT COALESCE(SUM(amount_per_day), 0) AS s FROM bookings
                   WHERE apartment_id = ? AND booking_date LIKE ?""",
                (apartment_id, f"{prefix}%"),
            )
        else:
            row = await self.fetchone(
                """SELECT COALESCE(SUM(amount_per_day), 0) AS s FROM bookings
                   WHERE booking_date LIKE ?""",
                (f"{prefix}%",),
            )
        return float(row["s"]) if row else 0.0

    async def occupied_days_count(
        self,
        apartment_id: int | None,
        year: int,
        month: int,
        up_to_day: int | None = None,
    ) -> int:
        prefix = f"{year:04d}-{month:02d}"
        if up_to_day:
            last = f"{prefix}-{up_to_day:02d}"
            if apartment_id:
                row = await self.fetchone(
                    """SELECT COUNT(DISTINCT booking_date) AS c FROM bookings
                       WHERE apartment_id = ? AND booking_date >= ? AND booking_date <= ?""",
                    (apartment_id, f"{prefix}-01", last),
                )
            else:
                row = await self.fetchone(
                    """SELECT COUNT(DISTINCT booking_date) AS c FROM bookings
                       WHERE booking_date >= ? AND booking_date <= ?""",
                    (f"{prefix}-01", last),
                )
        else:
            if apartment_id:
                row = await self.fetchone(
                    """SELECT COUNT(DISTINCT booking_date) AS c FROM bookings
                       WHERE apartment_id = ? AND booking_date LIKE ?""",
                    (apartment_id, f"{prefix}%"),
                )
            else:
                row = await self.fetchone(
                    """SELECT COUNT(DISTINCT booking_date) AS c FROM bookings
                       WHERE booking_date LIKE ?""",
                    (f"{prefix}%",),
                )
        return int(row["c"]) if row else 0

    async def total_apartment_days(
        self, apartment_id: int | None, year: int, month: int, up_to_day: int | None
    ) -> int:
        import calendar

        days_in_month = calendar.monthrange(year, month)[1]
        if up_to_day:
            return up_to_day * (1 if apartment_id else await self.apartment_count())
        return days_in_month * (1 if apartment_id else await self.apartment_count())

    async def apartment_count(self) -> int:
        row = await self.fetchone("SELECT COUNT(*) AS c FROM apartments")
        return int(row["c"]) if row else 0

    # --- finance ---
    async def add_finance(
        self,
        apartment_id: int | None,
        record_type: str,
        record_date: date,
        amount: float,
        category: str | None,
        comment: str | None,
    ) -> int:
        cur = await self.conn.execute(
            """INSERT INTO finance_records
               (apartment_id, record_type, record_date, amount, category, comment, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                apartment_id,
                record_type,
                record_date.isoformat(),
                amount,
                category,
                comment,
                datetime.utcnow().isoformat(),
            ),
        )
        await self.conn.commit()
        return cur.lastrowid

    async def delete_finance(self, record_id: int) -> None:
        await self.execute("DELETE FROM finance_records WHERE id = ?", (record_id,))

    async def get_finance(self, record_id: int) -> aiosqlite.Row | None:
        return await self.fetchone(
            "SELECT * FROM finance_records WHERE id = ?", (record_id,)
        )

    async def list_finance_history(self, limit: int = 30) -> list[aiosqlite.Row]:
        return await self.fetchall(
            """SELECT f.*, a.name AS apt_name FROM finance_records f
               LEFT JOIN apartments a ON a.id = f.apartment_id
               ORDER BY record_date DESC, id DESC LIMIT ?""",
            (limit,),
        )

    async def finance_sum_month(
        self,
        record_type: str,
        year: int,
        month: int,
        apartment_id: int | None = None,
    ) -> float:
        prefix = f"{year:04d}-{month:02d}"
        if apartment_id:
            row = await self.fetchone(
                """SELECT COALESCE(SUM(amount), 0) AS s FROM finance_records
                   WHERE record_type = ? AND apartment_id = ? AND record_date LIKE ?""",
                (record_type, apartment_id, f"{prefix}%"),
            )
        else:
            row = await self.fetchone(
                """SELECT COALESCE(SUM(amount), 0) AS s FROM finance_records
                   WHERE record_type = ? AND record_date LIKE ?""",
                (record_type, f"{prefix}%"),
            )
        return float(row["s"]) if row else 0.0

    async def finance_by_category_month(
        self,
        record_type: str,
        year: int,
        month: int,
        apartment_id: int,
    ) -> list[tuple[str, float]]:
        prefix = f"{year:04d}-{month:02d}"
        rows = await self.fetchall(
            """SELECT category, SUM(amount) AS s FROM finance_records
               WHERE record_type = ? AND apartment_id = ? AND record_date LIKE ?
               GROUP BY category""",
            (record_type, apartment_id, f"{prefix}%"),
        )
        return [(r["category"] or "Прочее", float(r["s"])) for r in rows]
