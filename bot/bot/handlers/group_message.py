from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone
from time import monotonic

from aiogram import F, Router
from aiogram.types import Message
from rapidfuzz import fuzz

from bot import conversation_tracker, group_cache, resolution_handler, role_cache
from bot.conversation_tracker import TrackedMsg
from bot.i18n import t
from bot.services import ai_answer_service, kb_client
from bot.services.classifier_service import ClassifyResult, classify
from bot.state_manager import StateManager
from bot.utils.formatters import format_match_reply
from config.logger import logger
from config.settings import settings
from database.connection import get_session
from database.models import User
from database.repositories import (
    HelpKeywordRepository,
    MessageClassificationRepository,
    UserRepository,
)

router = Router(name="group_message")

_GROUP_TYPES = {"group", "supergroup"}
CONFIDENCE_THRESHOLD = 0.7
KEYWORD_FUZZY_THRESHOLD = 75

_pending: dict[int, asyncio.Task] = {}

_kw_cache: list[str] = []
_kw_cache_at: float = 0.0
_KW_CACHE_TTL = 60.0


def cancel_pending(chat_id: int) -> None:
    task = _pending.pop(chat_id, None)
    if task:
        task.cancel()
        logger.info(f"30s timer bekor — inson javob berdi (chat={chat_id})")


def _lang(detected: str) -> str:
    return detected if detected in ("uz", "ru") else "uz"


def _detect_lang_simple(text: str) -> str:
    cyrillic = sum(1 for c in text if "Ѐ" <= c <= "ӿ")
    return "ru" if cyrillic > len(text) * 0.3 else "uz"


def _tracked_msg(user, text: str, is_support: bool) -> TrackedMsg:
    full_name = " ".join(filter(None, [
        getattr(user, "first_name", None),
        getattr(user, "last_name", None),
    ])) or str(user.id)
    return TrackedMsg(
        user_id=user.id,
        username=getattr(user, "username", None),
        display_name=full_name,
        is_support=is_support,
        text=text,
    )


# ── Keyword cache ─────────────────────────────────────────────────────────────

async def _get_keywords() -> list[str]:
    global _kw_cache, _kw_cache_at
    if monotonic() - _kw_cache_at > _KW_CACHE_TTL:
        try:
            async with get_session() as session:
                _kw_cache = await HelpKeywordRepository(session).list_phrases()
                _kw_cache_at = monotonic()
        except Exception as exc:
            logger.warning(f"Keyword cache yuklanmadi: {exc}")
    return _kw_cache


async def _keyword_match(text: str) -> str | None:
    keywords = await _get_keywords()
    text_norm = text.lower().strip()
    best_phrase, best_score = None, 0
    for kw in keywords:
        score = fuzz.partial_ratio(kw.lower(), text_norm)
        if score >= KEYWORD_FUZZY_THRESHOLD and score > best_score:
            best_phrase, best_score = kw, score
    return best_phrase


async def _save_keyword(phrase: str) -> None:
    phrase = phrase.strip()[:150]
    if len(phrase) < 3:
        return
    try:
        async with get_session() as session:
            await HelpKeywordRepository(session).add(phrase, source="ai")
        global _kw_cache_at
        _kw_cache_at = 0.0
    except Exception as exc:
        logger.warning(f"Keyword saqlanmadi: {exc}")


# ── @mention support + tracker ────────────────────────────────────────────────

async def _call_support(message: Message, lang: str, client_text: str) -> None:
    """Support topilmasa @mention bilan chaqiradi va suhbatni kuzatishni boshlaydi."""
    mentions = role_cache.get_support_mentions()
    user = message.from_user

    if mentions:
        mention_str = " ".join(mentions)
        if lang == "ru":
            text = (
                f"❓ По данному вопросу решения не найдено.\n"
                f"{mention_str} — нужна помощь!"
            )
        else:
            text = (
                f"❓ Bu muammo bo'yicha yechim topilmadi.\n"
                f"{mention_str} — yordam kerak!"
            )
        await message.reply(text)
    else:
        # Support aniqlanmagan → screenshot hint (varied)
        await message.reply(_random_screenshot_hint(lang))
        return

    # Suhbatni kuzatishni boshlash
    conversation_tracker.start(
        message.chat.id,
        _tracked_msg(user, client_text, is_support=False),
    )
    logger.info(
        f"[tracker] Suhbat kuzatish boshlandi: chat={message.chat.id}"
    )


# ── Delayed reply ─────────────────────────────────────────────────────────────

async def _delayed_reply(
    message: Message,
    lang: str,
    result: ClassifyResult | None,
    text: str,
    state_manager: StateManager,
    action_tag: str,
) -> None:
    try:
        await asyncio.sleep(30)
        has_detail = result.has_enough_detail if result else False

        # KB dan qidirish
        if has_detail and text:
            kb_match = await kb_client.search(text, lang)
            if kb_match:
                await message.reply(format_match_reply(
                    title=kb_match.title or "KB",
                    detected_text=text,
                    solution=kb_match.solution,
                    score=kb_match.similarity * 100,
                    lang=lang,
                ))
                await _log(user=message.from_user, chat_id=message.chat.id,
                           text=text, result=result, action="kb_text_match")
                return
            # Detail bor lekin KB miss → AI mustaqil javob bersin
            if settings.llm_enabled:
                from database.connection import get_session
                from database.repositories import ErrorRepository
                async with get_session() as session:
                    errors = list(await ErrorRepository(session).list_all())
                ai_ans = await ai_answer_service.generate(text, errors, lang)
                if ai_ans:
                    await message.reply(ai_ans.text)
                    await _log(user=message.from_user, chat_id=message.chat.id,
                               text=text, result=result, action="ai_answer")
                    logger.info(f"[ai-answer] Matn javob berildi chat={message.chat.id}")
                    return
            # AI ham javob bera olmadi → support chaqir
            await _call_support(message, lang, text)
            await _log(user=message.from_user, chat_id=message.chat.id,
                       text=text, result=result, action="called_support")
            logger.info(f"Support chaqirildi ({action_tag}) — chat={message.chat.id}")
        else:
            # Detail yetarli emas → screenshot hint (varied, majburiy emas)
            await message.reply(_random_screenshot_hint(lang))
            await _log(user=message.from_user, chat_id=message.chat.id,
                       text=text, result=result, action="asked_screenshot_hint")

    except asyncio.CancelledError:
        pass


# ── Varied replies ─────────────────────────────────────────────────────────────

_GREETINGS = {
    "uz": [
        "Salom! 👋",
        "Assalomu alaykum! 😊",
        "Xush kelibsiz! 🤖",
        "Salom-salom! 👋 Qanday yordam bera olaman?",
        "Salom! Muammo bo'lsa yordamlashaman. 🙂",
    ],
    "ru": [
        "Привет! 👋",
        "Здравствуйте! 😊",
        "Добрый день! 🤖",
        "Привет-привет! 👋 Чем могу помочь?",
        "Здравствуйте! Готов помочь. 🙂",
    ],
}

_SCREENSHOT_HINTS = {
    "uz": [
        "Xatolik screenshotini yuboring — qarab beraman. 📸",
        "Screenshot tashlasangiz, tezroq yordam bera olaman.",
        "Muammo screenshotini yuboring. 🖼",
        "Agar xatolik ekranda ko'rinsa — screenshot yuboring.",
    ],
    "ru": [
        "Пришлите скриншот ошибки — разберёмся. 📸",
        "Отправьте скриншот — помогу быстрее.",
        "Скриншот проблемы поможет разобраться. 🖼",
        "Если ошибка на экране — скиньте скриншот.",
    ],
}


def _random_greeting(lang: str) -> str:
    return random.choice(_GREETINGS.get(lang, _GREETINGS["uz"]))


def _random_screenshot_hint(lang: str) -> str:
    return random.choice(_SCREENSHOT_HINTS.get(lang, _SCREENSHOT_HINTS["uz"]))


# ── Main handler ──────────────────────────────────────────────────────────────

@router.message(F.chat.type.in_(_GROUP_TYPES), F.text)
async def handle_group_text(message: Message, state_manager: StateManager) -> None:
    user = message.from_user
    if user is None:
        return

    chat_id = message.chat.id

    if not group_cache.is_approved(chat_id):
        return

    text = (message.text or "").strip()
    if not text:
        return

    # ── Kuzatilayotgan suhbatga xabar qo'shish (har doim) ────────────────────
    is_supp = role_cache.is_support(user.id)
    if conversation_tracker.is_tracking(chat_id):
        conversation_tracker.add(chat_id, _tracked_msg(user, text, is_support=is_supp))

    # ── 1. Global support cache ───────────────────────────────────────────────
    if is_supp:
        cancel_pending(chat_id)
        role_cache.try_activate(chat_id, f"known support user present (user={user.id})")
        logger.info(f"[support] user={user.id} chat={chat_id} — jim turadi")
        return

    mode = role_cache.get_mode(chat_id)

    # ── 2. AI classify ─────────────────────────────────────────────────────────
    if not settings.llm_enabled:
        if mode == "observing":
            return
        # active + LLM yo'q → keyword
        cancel_pending(chat_id)
        matched_kw = await _keyword_match(text)
        if matched_kw:
            lang = await _get_user_lang(user.id) or _detect_lang_simple(text)
            asyncio.create_task(_increment_hit(matched_kw))
            task = asyncio.create_task(
                _delayed_reply(message, lang, None, text, state_manager, "keyword")
            )
            _pending[chat_id] = task
        return

    result = await classify(text)
    lang = _lang(result.language)
    await _update_user_lang(user.id, user.username, lang)

    logger.info(
        f"[cls] user={user.id} chat={chat_id} mode={mode} "
        f"type={result.message_type} support={result.is_support_message} "
        f"conf={result.confidence:.2f} lang={lang}"
    )

    # ── 2a. Muammo hal bo'ldi (klent tasdiqladi) ──────────────────────────────
    if result.message_type == "resolved" and conversation_tracker.is_tracking(chat_id):
        messages = conversation_tracker.stop_and_get(chat_id)
        logger.info(
            f"[resolved] chat={chat_id} user={user.id} — muammo hal bo'ldi, "
            f"darhol tahlil ({len(messages)} xabar)"
        )
        asyncio.create_task(resolution_handler.on_resolved(chat_id, messages))
        await _log(user=user, chat_id=chat_id, text=text, result=result, action="resolved_trigger")
        return

    # ── 2b. Support xodimi aniqlandi ──────────────────────────────────────────
    if result.is_support_message or result.message_type == "solution":
        full_name = " ".join(filter(None, [user.first_name, user.last_name])) or str(user.id)
        role_cache.mark_support(user.id, username=user.username, full_name=full_name)
        role_cache.try_activate(
            chat_id,
            f"support detected via AI (user={user.id}, type={result.message_type})"
        )
        cancel_pending(chat_id)
        await _log(user=user, chat_id=chat_id, text=text,
                   result=result, action="support_observed")
        return

    # ── 2b. Observing rejimi ──────────────────────────────────────────────────
    if mode == "observing":
        logger.info(
            f"[observing] chat={chat_id} user={user.id} "
            f"type={result.message_type} — hali kuzatmoqdamiz"
        )
        await _log(user=user, chat_id=chat_id, text=text,
                   result=result, action="observing")
        return

    # ── Active rejim ──────────────────────────────────────────────────────────
    cancel_pending(chat_id)

    # Salom/tabrik
    if result.message_type == "greeting" and result.confidence >= 0.6:
        await message.reply(_random_greeting(lang))
        await _log(user=user, chat_id=chat_id, text=text,
                   result=result, action="greeting_reply")
        return

    # Ma'lumot/boshqa → jim
    if result.message_type in ("informational", "other"):
        await _log(user=user, chat_id=chat_id, text=text,
                   result=result, action="silent")
        return

    # Ishonch past → jim
    if not result.is_help_request or result.confidence < CONFIDENCE_THRESHOLD:
        await _log(user=user, chat_id=chat_id, text=text,
                   result=result, action="silent")
        return

    # Yordam so'rovi → keyword save + 30s timer
    await _save_keyword(text)
    task = asyncio.create_task(
        _delayed_reply(message, lang, result, text, state_manager, "ai")
    )
    _pending[chat_id] = task
    logger.info(
        f"30s timer boshlandi (AI) — chat={chat_id} "
        f"conf={result.confidence:.2f} detail={result.has_enough_detail}"
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_user_lang(user_id: int) -> str | None:
    try:
        async with get_session() as session:
            return await UserRepository(session).get_language(user_id)
    except Exception:
        return None


async def _increment_hit(phrase: str) -> None:
    try:
        async with get_session() as session:
            await HelpKeywordRepository(session).increment_hit(phrase)
    except Exception:
        pass


async def _update_user_lang(user_id: int, username: str | None, lang: str) -> None:
    try:
        async with get_session() as session:
            repo = UserRepository(session)
            user = await repo.get(user_id)
            if user is None:
                session.add(User(telegram_id=user_id, username=username, language=lang))
            else:
                user.language = lang
                user.username = username
                user.updated_at = datetime.now(tz=timezone.utc)
    except Exception as exc:
        logger.warning(f"User lang yangilanmadi: {exc}")


async def _log(
    *,
    user: object,
    chat_id: int,
    text: str,
    result: ClassifyResult | None,
    action: str,
) -> None:
    try:
        async with get_session() as session:
            await MessageClassificationRepository(session).create(
                telegram_user=user.id,
                telegram_username=user.username,
                chat_id=chat_id,
                message_text=text[:500],
                language=result.language if result else None,
                is_help_request=result.is_help_request if result else None,
                confidence=result.confidence if result else None,
                action_taken=action,
            )
    except Exception as exc:
        logger.warning(f"Classification log xatoligi: {exc}")
