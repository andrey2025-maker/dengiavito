from aiogram import Router

from bot.handlers import (
    access,
    admin_handlers,
    apartments,
    booking,
    codes,
    excel_handlers,
    finances,
    menu,
    start,
    statistics,
)


def setup_routers() -> Router:
    root = Router()
    root.include_router(start.router)
    root.include_router(admin_handlers.router)
    root.include_router(excel_handlers.router)
    root.include_router(menu.router)
    root.include_router(codes.router)
    root.include_router(apartments.router)
    root.include_router(booking.router)
    root.include_router(finances.router)
    root.include_router(statistics.router)
    root.include_router(access.router)
    return root
