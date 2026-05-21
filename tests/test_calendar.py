from datetime import date

from aiogram.enums import ButtonStyle

from bot.services.calendar_kb import build_calendar, build_finance_calendar, dates_in_range


def test_dates_in_range():
    assert len(dates_in_range(date(2026, 5, 16), date(2026, 5, 18))) == 3


def test_booking_calendar_pay_button():
    from tests.conftest import all_callbacks

    kb = build_calendar(
        apartment_id=1,
        year=2026,
        month=5,
        booked={},
        anchor=date(2026, 5, 16),
        end=date(2026, 5, 18),
    )
    assert "cal_pay:1" in all_callbacks(kb)


def test_finance_calendar_has_apt_id():
    from tests.conftest import all_callbacks

    kb = build_finance_calendar(year=2026, month=5, apartment_id=7)
    cbs = all_callbacks(kb)
    assert any(c.startswith("fcal_d:7:") for c in cbs)
    assert "fin_can:7" in cbs


def test_booked_green():
    kb = build_calendar(
        apartment_id=1,
        year=2026,
        month=5,
        booked={"2026-05-10": 5000},
        anchor=None,
        end=None,
    )
    for row in kb.inline_keyboard:
        for btn in row:
            if btn.text == "10":
                assert btn.style == ButtonStyle.SUCCESS
