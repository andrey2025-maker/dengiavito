from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ButtonStyle

from bot.database import Database


def apartments_list_kb(
    apartments: list, *, prefix: str = "apt", add_new: bool = True
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for apt in apartments:
        builder.button(
            text=apt["name"],
            callback_data=f"{prefix}:{apt['id']}",
        )
    builder.adjust(1)
    if add_new:
        builder.row(
            InlineKeyboardButton(text="➕ Добавить квартиру", callback_data="apt_add")
        )
    return builder.as_markup()


def apartment_actions_kb(apt_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Ред.", callback_data=f"apt_edit:{apt_id}")
    builder.button(text="🗑 Удалить", callback_data=f"apt_del:{apt_id}")
    builder.row(
        InlineKeyboardButton(
            text="🔒 Закрыть даты", callback_data=f"apt_close:{apt_id}"
        )
    )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="apt_back"))
    builder.adjust(2, 1, 1)
    return builder.as_markup()


def confirm_delete_kb(apt_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, удалить",
                    callback_data=f"apt_del_yes:{apt_id}",
                    style=ButtonStyle.DANGER,
                ),
                InlineKeyboardButton(
                    text="❌ Отмена", callback_data=f"apt_del_no:{apt_id}"
                ),
            ]
        ]
    )


def add_mode_kb(apt_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📅 Календарь", callback_data=f"add_cal:{apt_id}"
                ),
                InlineKeyboardButton(
                    text="💰 Финансы", callback_data=f"add_fin:{apt_id}"
                ),
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="add_back")],
        ]
    )


def finance_hub_kb(apt_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Доход", callback_data=f"fin_i:{apt_id}"),
                InlineKeyboardButton(text="➖ Расход", callback_data=f"fin_o:{apt_id}"),
            ],
            [
                InlineKeyboardButton(
                    text="📋 История", callback_data=f"fin_lst:{apt_id}:0"
                )
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"add:{apt_id}")],
        ]
    )


INCOME_CATEGORIES = ("Доп. услуги", "Штраф гостю", "Прочее")
EXPENSE_CATEGORIES = (
    "🏠 Аренда",
    "🧹 Уборка",
    "💡 Коммуналка",
    "🔧 Ремонт",
    "📦 Расходники",
    "➕ Другое",
)


def finance_categories_kb(record_type: str) -> InlineKeyboardMarkup:
    cats = INCOME_CATEGORIES if record_type == "income" else EXPENSE_CATEGORIES
    builder = InlineKeyboardBuilder()
    for cat in cats:
        builder.button(text=cat, callback_data=f"fin_cat:{cat}")
    builder.adjust(2)
    builder.row(
        InlineKeyboardButton(text="⏭ Пропустить", callback_data="fin_cat_skip")
    )
    return builder.as_markup()


def skip_comment_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="fin_comment_skip")]
        ]
    )


def booking_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить",
                    callback_data="bok_confirm",
                    style=ButtonStyle.SUCCESS,
                ),
                InlineKeyboardButton(text="✏️ Изменить сумму", callback_data="bok_edit"),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена", callback_data="bok_cancel", style=ButtonStyle.DANGER
                )
            ],
        ]
    )


def payment_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="За всё время", callback_data="bok_pt:total"
                ),
                InlineKeyboardButton(text="За день", callback_data="bok_pt:day"),
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="bok_cancel")],
        ]
    )


def access_request_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Добавить",
                    callback_data=f"adm_add:{user_id}",
                    style=ButtonStyle.SUCCESS,
                ),
                InlineKeyboardButton(
                    text="Заблокировать",
                    callback_data=f"adm_block:{user_id}",
                    style=ButtonStyle.DANGER,
                ),
            ]
        ]
    )


async def admins_list_kb(db: Database) -> InlineKeyboardMarkup:
    admins = await db.get_admins()
    builder = InlineKeyboardBuilder()
    for adm in admins:
        if adm["is_owner"]:
            continue
        builder.button(
            text=f"🗑 {adm['name']}",
            callback_data=f"adm_rm:{adm['user_id']}",
        )
    builder.adjust(1)
    return builder.as_markup()


def stats_nav_kb(year: int, month: int) -> InlineKeyboardMarkup:
    prev_m, prev_y = (month - 1, year) if month > 1 else (12, year - 1)
    next_m, next_y = (month + 1, year) if month < 12 else (1, year + 1)
    months_ru = (
        "",
        "Январь",
        "Февраль",
        "Март",
        "Апрель",
        "Май",
        "Июнь",
        "Июль",
        "Август",
        "Сентябрь",
        "Октябрь",
        "Ноябрь",
        "Декабрь",
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"◀ {months_ru[prev_m]}",
                    callback_data=f"stat:{prev_y}:{prev_m}",
                ),
                InlineKeyboardButton(
                    text=f"{months_ru[next_m]} ▶",
                    callback_data=f"stat:{next_y}:{next_m}",
                ),
            ],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="stat_home")],
        ]
    )
