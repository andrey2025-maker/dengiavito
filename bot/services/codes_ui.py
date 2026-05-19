from __future__ import annotations

from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

BTN_TEXT_MAX = 58


def _truncate(name: str, max_len: int = BTN_TEXT_MAX) -> str:
    label = f"🏠 {name}"
    if len(label) <= max_len:
        return label
    return f"🏠 {name[: max_len - 4]}…"


def format_codes_text(apartments: list[Any]) -> str:
    lines = ["🔑 Коды квартир", ""]
    for apt in apartments:
        code = apt["door_code"] if apt["door_code"] else "—"
        lines.append(f"🏠 {apt['name']}")
        lines.append(f"Код: {code}")
        lines.append("")
    return "\n".join(lines).rstrip()


def build_codes_keyboard(apartments: list[Any]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for apt in apartments:
        rows.append(
            [
                InlineKeyboardButton(
                    text=_truncate(apt["name"]),
                    callback_data=f"code_sel:{apt['id']}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)
