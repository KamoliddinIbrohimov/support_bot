from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.types import Message, PhotoSize

from bot import conversation_tracker, group_cache, role_cache
from bot.conversation_tracker import TrackedMsg
from bot.i18n import t
from bot.services import ErrorFinderService
from bot.services import relevance_service, vision_service
from bot.services.ocr_service import claude_ocr, easyocr_only
from bot.services import kb_client
from bot.handlers.group_message import cancel_pending
from bot.state_manager import StateManager
from bot.utils.formatters import (
    format_empty_ocr_reply,
    format_match_reply,
    format_no_match_reply,
)
from bot.utils.storage import build_image_path
from config.logger import logger
from config.settings import settings
from database.connection import get_session
from database.repositories import ErrorRepository, OCRLogRepository, UserRepository

router = Router(name="photo")
error_finder = ErrorFinderService()


@router.message(F.photo)
async def handle_photo(message: Message, bot: Bot, state_manager: StateManager) -> None:
    photo: PhotoSize = message.photo[-1]
    user = message.from_user
    if user is None:
        return

    # Guruh bo'lsa — tasdiqlangan va active rejimda ekanini tekshir
    if message.chat.type in ("group", "supergroup"):
        if not group_cache.is_approved(message.chat.id):
            return
        if role_cache.get_mode(message.chat.id) == "observing":
            return

    image_path = build_image_path(chat_id=message.chat.id, user_id=user.id)
    cancel_pending(message.chat.id)

    try:
        await bot.download(photo, destination=image_path)
    except Exception as exc:
        logger.exception(f"Rasmni yuklashda xatolik: {exc}")
        lang = await _get_lang(user.id, user.language_code)
        await message.reply(t("download_error", lang))
        return

    logger.info(f"Rasm yuklandi: {image_path.name} (chat={message.chat.id}, user={user.id})")

    # ── Til aniqlash ──────────────────────────────────────────────────────────
    conv = await state_manager.get(user.id, message.chat.id)
    if conv and conv.status == "waiting_for_screenshot":
        lang = conv.language if conv.language in ("uz", "ru") else "uz"
        await state_manager.clear(user.id, message.chat.id)
    else:
        lang = await _get_lang(user.id, user.language_code)

    await _update_user_lang(user.id, user.username, lang)

    # ── Step 1: EasyOCR (lokal, bepul) ───────────────────────────────────────
    ocr_text, ocr_conf = await easyocr_only(image_path)
    ocr_source = "easyocr"

    # ── Step 2: Relevance check (text mavjud bo'lsa) ──────────────────────────
    if ocr_text:
        is_relevant = await relevance_service.check_relevance(ocr_text=ocr_text)
        if not is_relevant:
            await _log(message, str(image_path), ocr_text, ocr_conf, None, None, "out_of_scope")
            await message.reply(t("out_of_scope", lang))
            return
    elif not settings.vision_enabled:
        # OCR text yo'q va Vision AI yo'q — hech narsa qila olmaymiz
        await _log(message, str(image_path), None, None, None, None, "not_found")
        await message.reply(format_empty_ocr_reply(lang))
        return

    # ── Step 3: KB semantic search ────────────────────────────────────────────
    if ocr_text:
        kb_match = await kb_client.search(ocr_text, lang)
        if kb_match:
            logger.info(f"KB hit: similarity={kb_match.similarity:.2f}")
            await _log(message, str(image_path), ocr_text, ocr_conf, None, kb_match.similarity, "kb_match")
            await message.reply(format_match_reply(
                title=kb_match.title or "KB",
                detected_text=ocr_text,
                solution=kb_match.solution,
                score=kb_match.similarity * 100,
                lang=lang,
            ))
            # KB da video yo'q
            return

    # ── Step 4: Fuzzy match (Error DB) ───────────────────────────────────────
    async with get_session() as session:
        errors = list(await ErrorRepository(session).list_all())

    if ocr_text:
        fuzzy = error_finder.find_best(ocr_text, errors, lang)
        if fuzzy:
            await _log(
                message, str(image_path), ocr_text, ocr_conf,
                fuzzy.error.id, float(fuzzy.score), f"fuzzy_{ocr_source}",
            )
            await message.reply(format_match_reply(
                title=fuzzy.error.get_title(lang),
                detected_text=ocr_text,
                solution=fuzzy.error.get_solution(lang),
                score=fuzzy.score,
                lang=lang,
            ))
            await _send_video(message, fuzzy.error, lang)
            return

    # ── Step 5: AI OCR fallback — faqat KB+fuzzy fail bo'lgandan keyin ────────
    if settings.vision_enabled:
        logger.info("AI OCR: KB/fuzzy match topilmadi — AI bilan qayta o'qish")
        ai_text = await claude_ocr(image_path)

        if ai_text and ai_text != ocr_text:
            prev_empty = not ocr_text
            ocr_text = ai_text
            ocr_source = "ai"

            # Relevance re-check faqat avval text bo'lmagan bo'lsa
            if prev_empty:
                is_relevant = await relevance_service.check_relevance(ocr_text=ocr_text)
                if not is_relevant:
                    await _log(message, str(image_path), ocr_text, None, None, None, "out_of_scope")
                    await message.reply(t("out_of_scope", lang))
                    return

            # KB re-search
            kb_match = await kb_client.search(ocr_text, lang)
            if kb_match:
                logger.info(f"KB hit (AI OCR): similarity={kb_match.similarity:.2f}")
                await _log(message, str(image_path), ocr_text, None, None, kb_match.similarity, "kb_match")
                await message.reply(format_match_reply(
                    title=kb_match.title or "KB",
                    detected_text=ocr_text,
                    solution=kb_match.solution,
                    score=kb_match.similarity * 100,
                    lang=lang,
                ))
                return

            # Fuzzy re-match
            fuzzy = error_finder.find_best(ocr_text, errors, lang)
            if fuzzy:
                await _log(
                    message, str(image_path), ocr_text, None,
                    fuzzy.error.id, float(fuzzy.score), "fuzzy_ai",
                )
                await message.reply(format_match_reply(
                    title=fuzzy.error.get_title(lang),
                    detected_text=ocr_text,
                    solution=fuzzy.error.get_solution(lang),
                    score=fuzzy.score,
                    lang=lang,
                ))
                await _send_video(message, fuzzy.error, lang)
                return

    # ── Step 6: Vision AI — so'nggi chora ────────────────────────────────────
    vision = await vision_service.identify_error(
        image_path=image_path,
        ocr_text=ocr_text,
        errors=errors,
        lang=lang,
        user_id=user.id,
    )
    if vision:
        await _log(
            message, str(image_path), ocr_text, None,
            vision.error.id, vision.score, "vision_ai",
        )
        await message.reply(format_match_reply(
            title=vision.error.get_title(lang),
            detected_text=ocr_text,
            solution=vision.error.get_solution(lang),
            score=vision.score,
            lang=lang,
            via_vision=True,
        ))
        await _send_video(message, vision.error, lang)
        return

    # ── Not found ─────────────────────────────────────────────────────────────
    await _log(message, str(image_path), ocr_text or None, None, None, None, "not_found")

    is_group = message.chat.type in ("group", "supergroup")

    if not ocr_text:
        await message.reply(format_empty_ocr_reply(lang))
    elif is_group:
        # Guruhda: support ni chaqir va suhbatni kuzat
        mentions = role_cache.get_support_mentions()
        if mentions:
            mention_str = " ".join(mentions)
            if lang == "ru":
                call_text = (
                    f"❓ Скриншот распознан, но решение не найдено.\n"
                    f"{mention_str} — нужна помощь!"
                )
            else:
                call_text = (
                    f"❓ Screenshot tanildi, lekin yechim topilmadi.\n"
                    f"{mention_str} — yordam kerak!"
                )
            await message.reply(call_text)
            # Kuzatishni boshlash
            full_name = " ".join(filter(None, [user.first_name, user.last_name])) or str(user.id)
            conversation_tracker.start(
                message.chat.id,
                TrackedMsg(
                    user_id=user.id,
                    username=user.username,
                    display_name=full_name,
                    is_support=False,
                    text=f"[Screenshot] OCR: {ocr_text[:300]}",
                ),
            )
            logger.info(f"[tracker] Screenshot no-match: kuzatish boshlandi chat={message.chat.id}")
        else:
            sent = await message.reply(format_no_match_reply(ocr_text, lang))
            await state_manager.set_no_match_watch(
                bot_message_id=sent.message_id,
                chat_id=message.chat.id,
                ocr_text=ocr_text,
                lang=lang,
            )
    else:
        # Private chat: eski xulq
        sent = await message.reply(format_no_match_reply(ocr_text, lang))
        await state_manager.set_no_match_watch(
            bot_message_id=sent.message_id,
            chat_id=message.chat.id,
            ocr_text=ocr_text,
            lang=lang,
        )


async def _send_video(message: Message, error: object, lang: str) -> None:
    file_id = getattr(error, "solution_video_file_id", None)
    if not file_id:
        return
    from bot.i18n import t as _t
    try:
        await message.reply_video(
            video=file_id,
            caption=_t("match_video", lang),
        )
    except Exception as exc:
        logger.warning(f"Video yuborishda xatolik: {exc}")


async def _get_lang(user_id: int, language_code: str | None) -> str:
    try:
        async with get_session() as session:
            return await UserRepository(session).get_language(user_id)
    except Exception:
        return "ru" if language_code == "ru" else "uz"


async def _update_user_lang(user_id: int, username: str | None, lang: str) -> None:
    try:
        async with get_session() as session:
            repo = UserRepository(session)
            user = await repo.get(user_id)
            if user is None:
                from database.models import User
                user = User(telegram_id=user_id, username=username, language=lang)
                session.add(user)
            else:
                user.language = lang
    except Exception as exc:
        logger.warning(f"Could not update user lang: {exc}")


async def _log(
    message: Message,
    image_path: str,
    detected_text: str | None,
    confidence: float | None,
    matched_error_id: int | None,
    match_score: float | None,
    matched_via: str,
) -> None:
    try:
        async with get_session() as session:
            await OCRLogRepository(session).create(
                telegram_user=message.from_user.id,
                telegram_username=message.from_user.username,
                chat_id=message.chat.id,
                image_path=image_path,
                detected_text=detected_text,
                confidence=confidence,
                matched_error_id=matched_error_id,
                match_score=match_score,
                matched_via=matched_via,
            )
    except Exception as exc:
        logger.exception(f"OCR log xatolik: {exc}")
