from aiogram.types import CallbackQuery, Chat, Message, Update

from tests.conftest import make_user


def make_message(
    text: str,
    user_id: int,
    message_id: int = 1,
    *,
    username: str | None = None,
) -> Message:
    user = make_user(user_id, username=username)
    chat = Chat(id=user_id, type="private")
    return Message(
        message_id=message_id,
        date=1700000000,
        chat=chat,
        from_user=user,
        text=text,
    )


def message_update(text: str, user_id: int, update_id: int = 1) -> Update:
    return Update(update_id=update_id, message=make_message(text, user_id))


def make_callback(
    data: str,
    user_id: int,
    message: Message | None = None,
    callback_id: str = "cb1",
) -> CallbackQuery:
    msg = message or make_message("placeholder", user_id, message_id=10)
    return CallbackQuery(
        id=callback_id,
        from_user=make_user(user_id),
        chat_instance="ci",
        data=data,
        message=msg,
    )


def callback_update(
    data: str,
    user_id: int,
    update_id: int = 1,
    message: Message | None = None,
) -> Update:
    return Update(
        update_id=update_id,
        callback_query=make_callback(data, user_id, message=message),
    )
