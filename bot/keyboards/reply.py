from datetime import date

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

MAIN_MENU_BUTTONS = (
    ("📊 Статистика", "➕ Добавление"),
    ("⚙️ Мои квартиры", "🔑 Коды"),
)


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=row[0]), KeyboardButton(text=row[1])]
        for row in MAIN_MENU_BUTTONS
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def main_menu_text(today: date | None = None) -> str:
    d = today or date.today()
    return f"🏠 Главное меню\nСегодня: {d.strftime('%d.%m.%Y')}"
