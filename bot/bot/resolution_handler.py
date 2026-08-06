"""Called when a tracked conversation reaches inactivity timeout.

Steps:
1. Send transcript to AI → extract title, keywords, solution (ru+uz)
2. Save to errors DB automatically
3. Notify all admins: "Yangi yechim saqlandi" with entry details
"""

from __future__ import annotations

from aiogram import Bot

from bot.conversation_tracker import TrackedMsg
from bot.services import resolution_service
from config.logger import logger
from config.settings import settings
from database.connection import get_session
from database.repositories import ErrorRepository

_bot: Bot | None = None


def set_bot(bot: Bot) -> None:
    global _bot
    _bot = bot


async def on_resolved(chat_id: int, messages: list[TrackedMsg]) -> None:
    """Triggered by conversation_tracker after INACTIVITY_SECS of silence."""
    logger.info(
        f"[resolution] Suhbat tahlil qilinmoqda: chat={chat_id} "
        f"messages={len(messages)}"
    )

    entry = await resolution_service.analyze(messages)
    if entry is None:
        logger.info(f"[resolution] chat={chat_id} — yechim topilmadi, saqlanmadi")
        return

    # ── Save to errors DB ─────────────────────────────────────────────────────
    kw_list = [k.strip() for k in entry.keywords.split(",") if k.strip()]

    try:
        async with get_session() as session:
            saved = await ErrorRepository(session).create(
                title=entry.title_ru,
                keywords=kw_list,
                solution=entry.solution_ru,
                title_ru=entry.title_ru,
                title_uz=entry.title_uz,
                keywords_ru=kw_list,
                keywords_uz=kw_list,
                solution_ru=entry.solution_ru,
                solution_uz=entry.solution_uz,
            )
        logger.info(
            f"[resolution] Yangi xatolik saqlandi: id={saved.id} "
            f"title={entry.title_ru!r}"
        )
    except Exception as exc:
        logger.exception(f"[resolution] DB saqlashda xatolik: {exc}")
        return

    # ── Notify admins ──────────────────────────────────────────────────────────
    if _bot is None:
        return

    preview_ru = entry.solution_ru[:200] + ("…" if len(entry.solution_ru) > 200 else "")
    text = (
        f"🧠 <b>Yangi yechim avtomatik saqlandi</b>\n\n"
        f"📌 <b>ID:</b> <code>{saved.id}</code>\n"
        f"🇷🇺 <b>Nomi:</b> {entry.title_ru}\n"
        f"🇺🇿 <b>Nomi:</b> {entry.title_uz}\n"
        f"🔑 <b>Keywords:</b> {entry.keywords}\n\n"
        f"<b>Yechim (RU):</b>\n{preview_ru}\n\n"
        f"📂 Guruh: <code>{chat_id}</code>\n"
        f"💬 Xabarlar soni: {len(messages)}\n\n"
        f"✏️ Tahrirlash: /add_error yoki to'g'ridan API"
    )

    for admin_id in settings.ADMIN_IDS:
        try:
            await _bot.send_message(admin_id, text)
        except Exception as exc:
            logger.warning(f"Adminga xabar yuborilmadi ({admin_id}): {exc}")
