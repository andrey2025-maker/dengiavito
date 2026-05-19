from aiogram import Bot, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database import Database
from bot.filters.access import IsAdminFilter
from bot.services.codes_ui import build_codes_keyboard, format_codes_text
from bot.states import CodeEditForm

router = Router()


@router.message(IsAdminFilter(), F.text == "🔑 Коды")
async def codes_menu(message: Message, db: Database) -> None:
    apts = await db.list_apartments()
    if not apts:
        await message.answer("Квартир пока нет. Добавьте их в «⚙️ Мои квартиры».")
        return
    await message.answer(
        format_codes_text(apts),
        reply_markup=build_codes_keyboard(apts),
    )


@router.callback_query(IsAdminFilter(), F.data.startswith("code_sel:"))
async def code_select_apartment(
    callback: CallbackQuery, state: FSMContext, db: Database
) -> None:
    apt_id = int(callback.data.split(":")[1])
    apt = await db.get_apartment(apt_id)
    if not apt:
        await callback.answer("Квартира не найдена", show_alert=True)
        return
    if not callback.message:
        await callback.answer()
        return
    await state.set_state(CodeEditForm.new_code)
    await state.update_data(
        apt_id=apt_id,
        panel_message_id=callback.message.message_id,
        panel_chat_id=callback.message.chat.id,
    )
    await callback.message.answer(
        f'Введите новый код для «{apt["name"]}» (или «-» чтобы сбросить):'
    )
    await callback.answer()


@router.message(IsAdminFilter(), CodeEditForm.new_code)
async def code_save_new(
    message: Message, state: FSMContext, db: Database, bot: Bot
) -> None:
    raw = (message.text or "").strip()
    if not raw:
        await message.answer("Код не может быть пустым. Введите снова или «-» для сброса:")
        return
    if len(raw) > 64:
        await message.answer("Слишком длинный код (макс. 64 символа). Введите короче:")
        return

    data = await state.get_data()
    apt_id = data.get("apt_id")
    msg_id = data.get("panel_message_id")
    chat_id = data.get("panel_chat_id")
    if not apt_id or msg_id is None or chat_id is None:
        await state.clear()
        await message.answer("Сессия устарела. Откройте «🔑 Коды» снова.")
        return

    code = None if raw in ("-", "—") else raw
    await db.update_apartment_door_code(apt_id, code)
    await state.clear()

    apts = await db.list_apartments()
    text = format_codes_text(apts)
    kb = build_codes_keyboard(apts)
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=text,
            reply_markup=kb,
        )
    except Exception:
        await message.answer("Код сохранён, но не удалось обновить список. Откройте «🔑 Коды» ещё раз.")
        await message.answer("✅ Код обновлён.")
        return

    await message.answer("✅ Код обновлён.")
