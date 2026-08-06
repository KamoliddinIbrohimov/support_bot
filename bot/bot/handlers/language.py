from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.i18n import t
from config.logger import logger
from database.connection import get_session
from database.repositories import UserRepository

router = Router(name="language")


def _language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="set_lang:uz"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang:ru"),
            ]
        ]
    )


@router.message(Command("language"), F.chat.type == "private")
async def cmd_language_private(message: Message) -> None:
    async with get_session() as session:
        repo = UserRepository(session)
        user = await repo.get_or_create(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            language_code=message.from_user.language_code,
        )
        lang = user.language

    await message.answer(t("language_choose", lang), reply_markup=_language_keyboard())


@router.message(
    Command("language"),
    F.chat.type.in_({"group", "supergroup"}),
)
async def cmd_language_group(message: Message) -> None:
    # Detect user's current language as best we can without creating user
    async with get_session() as session:
        repo = UserRepository(session)
        lang = await repo.get_language(message.from_user.id)
    await message.reply(t("language_dm_only", lang))


@router.callback_query(F.data.startswith("set_lang:"))
async def cb_set_language(callback: CallbackQuery) -> None:
    lang = callback.data.split(":")[1]
    if lang not in ("uz", "ru"):
        await callback.answer()
        return

    async with get_session() as session:
        repo = UserRepository(session)
        await repo.set_language(callback.from_user.id, lang)

    logger.info(f"Language set: user={callback.from_user.id} lang={lang}")
    key = "language_set_uz" if lang == "uz" else "language_set_ru"
    await callback.message.edit_text(t(key, lang))
    await callback.answer()
