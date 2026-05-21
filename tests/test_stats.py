from datetime import date

import pytest

from bot.services.stats import build_stats_text


@pytest.mark.asyncio
async def test_stats_expandable_blockquote(db):
    aid = await db.add_apartment("Леонова, 41/2", None)
    await db.add_finance(aid, "expense", date(2026, 5, 1), 37000, "🏠 Аренда", None)
    text = await build_stats_text(db, 2026, 5, date(2026, 5, 19))
    assert "blockquote expandable" in text
    assert "Леонова" in text
    assert "37 000" in text or "37000" in text.replace(" ", "")
    assert "Финансовый результат" in text


@pytest.mark.asyncio
async def test_stats_escapes_html(db):
    aid = await db.add_apartment("<Test & Co>", None)
    text = await build_stats_text(db, 2026, 5, date(2026, 5, 1))
    assert "&lt;Test &amp; Co&gt;" in text
