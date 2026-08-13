"""Called when a tracked conversation reaches inactivity timeout.

Steps:
1. Send transcript to AI → extract title, keywords, solution (ru+uz)
2. Errors DB dan o'xshash entry qidirish (fuzzy match):
   - O'xshash topilsa + yangi yechim uzunroq (aniqroq) → yangilaydi
   - O'xshash topilsa + mavjud yechim yaxshiroq → saqlanmaydi
   - O'xshash topilmasa → yangi entry yaratadi
3. Notify all admins
"""

from __future__ import annotations

from aiogram import Bot
from rapidfuzz import fuzz

from bot.conversation_tracker import TrackedMsg
from bot.services import resolution_service
from config.logger import logger
from config.settings import settings
from database.connection import get_session
from database.repositories import ErrorRepository

_bot: Bot | None = None

DUPLICATE_THRESHOLD = 80  # title o'xshashligi uchun min score


def set_bot(bot: Bot) -> None:
    global _bot
    _bot = bot


def _similarity(a: str, b: str) -> float:
    a, b = a.lower().strip(), b.lower().strip()
    return max(fuzz.partial_ratio(a, b), fuzz.token_set_ratio(a, b))


def _is_clearer(new_sol: str, old_sol: str) -> bool:
    """Yangi yechim aniqroqmi — uzunlik asosiy mezon."""
    return len(new_sol.strip()) > len(old_sol.strip())


async def on_resolved(chat_id: int, messages: list[TrackedMsg]) -> None:
    logger.info(
        f"[resolution] Suhbat tahlil qilinmoqda: chat={chat_id} "
        f"messages={len(messages)}"
    )

    entry = await resolution_service.analyze(messages)
    if entry is None:
        logger.info(f"[resolution] chat={chat_id} — yechim topilmadi, saqlanmadi")
        return

    kw_list = [k.strip() for k in entry.keywords.split(",") if k.strip()]

    # Support xabarlaridan media file_id (oxirgi media ustunlik qiladi)
    solution_video_file_id = None
    solution_image_file_id = None
    for msg in reversed(messages):
        if msg.is_support:
            if not solution_video_file_id and msg.video_file_id:
                solution_video_file_id = msg.video_file_id
            if not solution_image_file_id and msg.photo_file_id:
                solution_image_file_id = msg.photo_file_id
            if solution_video_file_id and solution_image_file_id:
                break

    # ── Errors DB dan o'xshash entry qidirish ─────────────────────────────────
    action = "created"
    saved_id = None

    try:
        async with get_session() as session:
            repo = ErrorRepository(session)
            all_errors = list(await repo.list_all())

            # Title bo'yicha o'xshashlik tekshirish
            duplicate = None
            best_score = 0.0
            for err in all_errors:
                score = max(
                    _similarity(entry.title_ru, err.title_ru or ""),
                    _similarity(entry.title_ru, err.title or ""),
                )
                if score > best_score:
                    best_score = score
                    duplicate = err

            if duplicate and best_score >= DUPLICATE_THRESHOLD:
                existing_sol = duplicate.solution_ru or duplicate.solution or ""
                if _is_clearer(entry.solution_ru, existing_sol):
                    # Yangi yechim aniqroq → yangilaydi
                    await repo.update_solution(
                        duplicate.id,
                        solution_ru=entry.solution_ru,
                        solution_uz=entry.solution_uz,
                        keywords_ru=kw_list,
                        keywords_uz=kw_list,
                        solution_video_file_id=solution_video_file_id,
                        solution_image_file_id=solution_image_file_id,
                    )
                    saved_id = duplicate.id
                    action = "updated"
                    logger.info(
                        f"[resolution] Mavjud entry yangilandi: id={duplicate.id} "
                        f"score={best_score:.0f}%"
                    )
                else:
                    # Mavjud yechim yaxshiroq → o'zgartirilmaydi
                    saved_id = duplicate.id
                    action = "skipped"
                    logger.info(
                        f"[resolution] Mavjud entry aniqroq — o'zgartirilmadi: "
                        f"id={duplicate.id} score={best_score:.0f}%"
                    )
            else:
                # O'xshash topilmadi → yangi entry
                saved = await repo.create(
                    title=entry.title_ru,
                    keywords=kw_list,
                    solution=entry.solution_ru,
                    title_ru=entry.title_ru,
                    title_uz=entry.title_uz,
                    keywords_ru=kw_list,
                    keywords_uz=kw_list,
                    solution_ru=entry.solution_ru,
                    solution_uz=entry.solution_uz,
                    solution_video_file_id=solution_video_file_id,
                    solution_image_file_id=solution_image_file_id,
                )
                saved_id = saved.id
                logger.info(
                    f"[resolution] Yangi xatolik saqlandi: id={saved.id} "
                    f"title={entry.title_ru!r}"
                )
    except Exception as exc:
        logger.exception(f"[resolution] DB saqlashda xatolik: {exc}")
        return

    if action == "skipped":
        return

    # ── Notify admins ─────────────────────────────────────────────────────────
    if _bot is None:
        return

    preview_ru = entry.solution_ru[:200] + ("…" if len(entry.solution_ru) > 200 else "")
    media_info = ""
    if solution_video_file_id:
        media_info += "🎥 Video yechim saqlandi\n"
    if solution_image_file_id:
        media_info += "🖼 Rasm yechim saqlandi\n"

    action_label = "♻️ Mavjud yechim yangilandi" if action == "updated" else "🧠 Yangi yechim saqlandi"

    text = (
        f"{action_label}\n\n"
        f"📌 <b>ID:</b> <code>{saved_id}</code>\n"
        f"🇷🇺 <b>Nomi:</b> {entry.title_ru}\n"
        f"🇺🇿 <b>Nomi:</b> {entry.title_uz}\n"
        f"🔑 <b>Keywords:</b> {entry.keywords}\n\n"
        f"<b>Yechim (RU):</b>\n{preview_ru}\n\n"
        f"{media_info}"
        f"📂 Guruh: <code>{chat_id}</code>\n"
        f"💬 Xabarlar soni: {len(messages)}"
    )

    for admin_id in settings.ADMIN_IDS:
        try:
            await _bot.send_message(admin_id, text)
        except Exception as exc:
            logger.warning(f"Adminga xabar yuborilmadi ({admin_id}): {exc}")
