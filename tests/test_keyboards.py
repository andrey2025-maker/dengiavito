from bot.keyboards.inline import finance_hub_kb, stats_nav_kb
from bot.keyboards.reply import MAIN_MENU_BUTTONS, main_menu_keyboard
from tests.conftest import all_callbacks


def test_main_menu_no_global_finances():
    texts = [btn.text for row in main_menu_keyboard().keyboard for btn in row]
    assert "💰 Финансы" not in texts
    assert "🔑 Коды" in texts


def test_finance_hub_callbacks():
    cbs = all_callbacks(finance_hub_kb(3))
    assert "fin_i:3" in cbs
    assert "fin_o:3" in cbs
    assert "fin_lst:3:0" in cbs


def test_stats_nav():
    cbs = all_callbacks(stats_nav_kb(2026, 5))
    assert "stat:2026:4" in cbs
    assert "stat:2026:6" in cbs
