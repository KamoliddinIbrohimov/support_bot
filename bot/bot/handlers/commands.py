from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.i18n import t
from bot.utils.formatters import format_errors_list
from config.logger import logger
from database.connection import get_session
from database.repositories import ErrorRepository, UserRepository

router = Router(name="commands")


async def _get_lang(message: Message) -> str:
    async with get_session() as session:
        repo = UserRepository(session)
        user = await repo.get_or_create(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            language_code=message.from_user.language_code,
        )
        return user.language


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    lang = await _get_lang(message)
    await message.answer(t("start", lang))


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    lang = await _get_lang(message)
    await message.answer(t("help", lang))


@router.message(Command("errors"))
async def cmd_errors(message: Message) -> None:
    lang = await _get_lang(message)
    async with get_session() as session:
        repo = ErrorRepository(session)
        errors = list(await repo.list_all())

    logger.info(f"/errors: {len(errors)} ta yozuv chiqarildi user={message.from_user.id}")
    await message.answer(format_errors_list(errors, lang))


@router.message(
    Command("help"),
    F.chat.type.in_({"group", "supergroup"}),
)
async def cmd_help_group(message: Message) -> None:
    lang = await _get_lang(message)
    await message.reply(t("help", lang))
