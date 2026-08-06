from aiogram import Router

from bot.handlers import admin, chat_member, commands, group_message, language, photo, support_reply


def get_all_routers() -> list[Router]:
    return [
        chat_member.router,     # bot guruhga qo'shildi/chiqarildi + approve/reject
        support_reply.router,   # replies to bot messages (KB learning)
        group_message.router,   # group text classification
        commands.router,
        admin.router,
        language.router,
        photo.router,
    ]


__all__ = ["get_all_routers"]
