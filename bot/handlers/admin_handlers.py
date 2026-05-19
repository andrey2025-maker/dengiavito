from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Settings
from bot.database import Database
from bot.filters.access import IsAdminFilter
from bot.keyboards.inline import access_request_kb, admins_list_kb
from bot.keyboards.reply import main_menu_keyboard, main_menu_text
from bot.states import AdminAddFlow

router = Router()


@router.message(Command("admin"), IsAdminFilter())
async def cmd_admin(message: Message, db: Database, settings: Settings) -> None:
    if message.from_user and message.from_user.id != settings.owner_id:
        await message.answer("Команда доступна только владельцу.")
        return
    admins = await db.get_admins()
    lines = ["👥 Администраторы:\n"]
    for adm in admins:
        tag = " (владелец)" if adm["is_owner"] else ""
        lines.append(
            f'• <a href="tg://user?id={adm["user_id"]}">{adm["name"]}</a>{tag}'
        )
    kb = await admins_list_kb(db)
    await message.answer("\n".join(lines), reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("adm_add:"))
async def adm_add_start(callback: CallbackQuery, state: FSMContext, settings: Settings) -> None:
    if callback.from_user.id != settings.owner_id:
        await callback.answer("Только владелец", show_alert=True)
        return
    user_id = int(callback.data.split(":")[1])
    await state.update_data(new_admin_id=user_id)
    await state.set_state(AdminAddFlow.name)
    await callback.message.answer("Введите имя для нового администратора:")
    await callback.answer()


@router.message(AdminAddFlow.name, F.chat.type == "private")
async def adm_add_name(
    message: Message, state: FSMContext, db: Database, bot: Bot
) -> None:
    data = await state.get_data()
    user_id = data.get("new_admin_id")
    if not user_id:
        await state.clear()
        return
    name = (message.text or "").strip()
    if not name:
        await message.answer("Имя не может быть пустым. Повторите:")
        return
    await db.add_admin(user_id, name)
    await state.clear()
    await message.answer(f"Администратор «{name}» добавлен.")
    try:
        await bot.send_message(
            user_id,
            main_menu_text(),
            reply_markup=main_menu_keyboard(),
        )
    except Exception:
        await message.answer("Не удалось отправить сообщение пользователю.")


@router.callback_query(F.data.startswith("adm_block:"))
async def adm_block(callback: CallbackQuery, db: Database, settings: Settings) -> None:
    if callback.from_user.id != settings.owner_id:
        await callback.answer("Только владелец", show_alert=True)
        return
    user_id = int(callback.data.split(":")[1])
    await db.block_user(user_id)
    await callback.message.edit_text(
        callback.message.text + "\n\n⛔ Пользователь заблокирован."
    )
    await callback.answer("Заблокирован")


@router.callback_query(F.data.startswith("adm_rm:"))
async def adm_remove(callback: CallbackQuery, db: Database, settings: Settings) -> None:
    if callback.from_user.id != settings.owner_id:
        await callback.answer("Только владелец", show_alert=True)
        return
    user_id = int(callback.data.split(":")[1])
    await db.remove_admin(user_id)
    await callback.answer("Удалён")
    kb = await admins_list_kb(db)
    await callback.message.edit_reply_markup(reply_markup=kb)
