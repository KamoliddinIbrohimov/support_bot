from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone
from time import monotonic

from aiogram import Bot, F, Router
from aiogram.enums import ChatAction
from aiogram.types import Message
from rapidfuzz import fuzz

from bot import bot_context, conversation_tracker, group_cache, resolution_handler, role_cache
from bot.services import ErrorFinderService
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
    ErrorRepository,
    HelpKeywordRepository,
    MessageClassificationRepository,
    UserRepository,
)

router = Router(name="group_message")
_error_finder = ErrorFinderService()

_GROUP_TYPES = {"group", "supergroup"}
CONFIDENCE_THRESHOLD = 0.7
KEYWORD_FUZZY_THRESHOLD = 75

# (chat_id, user_id) → task: har bir foydalanuvchi alohida kuzatiladi
_pending: dict[tuple[int, int], asyncio.Task] = {}

# Bot yechim bergan vaqt (gratitude va follow-up uchun)
_solved_at: dict[tuple[int, int], float] = {}
_followup_tasks: dict[tuple[int, int], asyncio.Task] = {}

SOLVED_TTL = 600    # 10 daqiqa ichida "rahmat" → bot yechgan deb hisoblanadi
FOLLOWUP_DELAY = 300  # Yechim bergandan 5 daqiqa o'tsa — tekshirish

_kw_cache: list[str] = []
_kw_cache_at: float = 0.0
_KW_CACHE_TTL = 60.0


def cancel_pending(chat_id: int, user_id: int | None = None) -> None:
    if user_id is not None:
        task = _pending.pop((chat_id, user_id), None)
        if task:
            task.cancel()
            logger.info(f"30s timer bekor (chat={chat_id} user={user_id})")
    else:
        # photo.py dan chat_id bilan chaqiriladi — shu chatdagi barchasini bekor
        keys = [k for k in _pending if k[0] == chat_id]
        for k in keys:
            task = _pending.pop(k, None)
            if task:
                task.cancel()


def mark_solved(chat_id: int, user_id: int) -> None:
    _solved_at[(chat_id, user_id)] = monotonic()


def was_recently_solved(chat_id: int, user_id: int) -> bool:
    ts = _solved_at.get((chat_id, user_id))
    return ts is not None and monotonic() - ts < SOLVED_TTL


def cancel_followup(chat_id: int, user_id: int) -> None:
    task = _followup_tasks.pop((chat_id, user_id), None)
    if task:
        task.cancel()


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
    bot: Bot,
    lang: str,
    result: ClassifyResult | None,
    text: str,
    state_manager: StateManager,
    action_tag: str,
) -> None:
    try:
        await asyncio.sleep(30)
        has_detail = result.has_enough_detail if result else False

        # Izlayotganda "yozmoqda..." ko'rsatish
        try:
            await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        except Exception:
            pass

        # Errors DB dan yuklaymiz (KB + fuzzy + AI uchun kerak)
        async with get_session() as session:
            errors = list(await ErrorRepository(session).list_all())

        # 1. KB semantic search
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
                mark_solved(message.chat.id, message.from_user.id)
                start_followup(message, lang)
                return

        # 2. Errors DB fuzzy match (matn orqali ham topilishi kerak)
        if text:
            fuzzy = _error_finder.find_best(text, errors, lang)
            if fuzzy:
                reply_text = format_match_reply(
                    title=fuzzy.error.get_title(lang),
                    detected_text=text,
                    solution=fuzzy.error.get_solution(lang),
                    score=fuzzy.score,
                    lang=lang,
                )
                await _send_match_with_media(message, fuzzy.error, reply_text)
                await _log(user=message.from_user, chat_id=message.chat.id,
                           text=text, result=result, action="fuzzy_text_match")
                logger.info(f"[fuzzy-text] chat={message.chat.id} score={fuzzy.score:.0f}")
                mark_solved(message.chat.id, message.from_user.id)
                start_followup(message, lang)
                return

        # 3. AI mustaqil javob
        if settings.llm_enabled and text:
            ai_ans = await ai_answer_service.generate(text, errors, lang)
            if ai_ans:
                await message.reply(ai_ans.text)
                await _log(user=message.from_user, chat_id=message.chat.id,
                           text=text, result=result, action="ai_answer")
                logger.info(f"[ai-answer] Matn javob berildi chat={message.chat.id}")
                mark_solved(message.chat.id, message.from_user.id)
                start_followup(message, lang)
                return

        # 4. Hech narsa topilmadi → support chaqir
        await _call_support(message, lang, text)
        await _log(user=message.from_user, chat_id=message.chat.id,
                   text=text, result=result, action="called_support")
        logger.info(f"Support chaqirildi ({action_tag}) — chat={message.chat.id}")

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


_GRATITUDE_REPLIES = {
    "uz": [
        "Xursand bo'ldim! 😊 Boshqa savol bo'lsa, yozing.",
        "Iltimos! 👍 Yana yordam kerak bo'lsa, doim shu yerda.",
        "Salomat bo'ling! 🙂 Muammo bo'lsa, qaytib keling.",
        "Barakalla! 😊 Qo'shimcha savol bo'lsa — yozing.",
    ],
    "ru": [
        "Рад помочь! 😊 Если что — пишите.",
        "Пожалуйста! 👍 Обращайтесь, всегда готов помочь.",
        "Будьте здоровы! 🙂 Если возникнут вопросы — пишите.",
        "Отлично! 😊 Удачи! Если нужна помощь — обращайтесь.",
    ],
}

_FOLLOWUP_MSGS = {
    "uz": [
        "Muammo hal bo'ldimi? 🤔 Agar yana yordam kerak bo'lsa — yozing!",
        "Hamma narsa yaxshimi? Savol bo'lsa, qo'rqmay yozing. 😊",
        "Yechim yordam berdimi? Boshqa savol bo'lsa — men shu yerdaman.",
    ],
    "ru": [
        "Проблема решилась? 🤔 Если нужна помощь — пишите!",
        "Всё получилось? Если есть вопросы — обращайтесь. 😊",
        "Решение помогло? Если что-то ещё — я здесь.",
    ],
}

_UNSUPPORTED_MEDIA = {
    "uz": "📸 Iltimos, xatolikni <b>screenshot</b> (rasm) yoki <b>matn</b> ko'rinishida yuboring.",
    "ru": "📸 Пожалуйста, отправьте ошибку в виде <b>скриншота</b> или <b>текста</b>.",
}


async def _send_followup(message: Message, lang: str) -> None:
    try:
        await asyncio.sleep(FOLLOWUP_DELAY)
        key = (message.chat.id, message.from_user.id)
        _followup_tasks.pop(key, None)
        replies = _FOLLOWUP_MSGS.get(lang, _FOLLOWUP_MSGS["uz"])
        await message.reply(random.choice(replies))
    except asyncio.CancelledError:
        pass


def start_followup(message: Message, lang: str) -> None:
    key = (message.chat.id, message.from_user.id)
    old = _followup_tasks.pop(key, None)
    if old:
        old.cancel()
    _followup_tasks[key] = asyncio.create_task(_send_followup(message, lang))


# ── Bot mention handler ───────────────────────────────────────────────────────

def _extract_mention_question(message: Message, bot_username: str) -> str | None:
    """@bot_username mention bo'lsa, savolni qaytaradi. Bo'lmasa None."""
    if not message.text or not message.entities:
        return None
    mention_tag = f"@{bot_username}".lower()
    for ent in message.entities:
        if ent.type == "mention":
            chunk = message.text[ent.offset: ent.offset + ent.length].lower()
            if chunk == mention_tag:
                question = message.text.replace(
                    message.text[ent.offset: ent.offset + ent.length], ""
                ).strip()
                return question or None
    return None


# ── Unsupported media handler ─────────────────────────────────────────────────

@router.message(
    F.chat.type.in_(_GROUP_TYPES),
    F.video | F.voice | F.audio | F.document | F.sticker | F.animation,
)
async def handle_unsupported_media(message: Message) -> None:
    if not group_cache.is_approved(message.chat.id):
        return
    if role_cache.get_mode(message.chat.id) == "observing":
        return
    user = message.from_user
    if user is None or role_cache.is_support(user.id):
        return  # support xodimining mediasiga aralashmaymiz
    # Stiker — javob bermaymiz
    if message.sticker or message.animation:
        return
    lang = await _get_user_lang(user.id) or "uz"
    await message.reply(_UNSUPPORTED_MEDIA.get(lang, _UNSUPPORTED_MEDIA["uz"]))


# ── Main handler ──────────────────────────────────────────────────────────────

@router.message(F.chat.type.in_(_GROUP_TYPES), F.text)
async def handle_group_text(message: Message, bot: Bot, state_manager: StateManager) -> None:
    user = message.from_user
    if user is None:
        return

    chat_id = message.chat.id

    if not group_cache.is_approved(chat_id):
        return

    text = (message.text or "").strip()
    if not text:
        return

    # ── Xabar keldi — follow-up timer bekor, tracker yangilanadi ─────────────
    cancel_followup(chat_id, user.id)

    # ── @bot_username mention → darhol AI javob (30s kutmasdan) ──────────────
    bot_username = bot_context.bot_username
    if bot_username:
        question = _extract_mention_question(message, bot_username)
        if question:
            lang = await _get_user_lang(user.id) or _detect_lang_simple(question)
            logger.info(f"[mention] user={user.id} chat={chat_id} q={question[:60]!r}")
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            async with get_session() as session:
                errors = list(await ErrorRepository(session).list_all())
            fuzzy = _error_finder.find_best(question, errors, lang)
            if fuzzy:
                reply_text = format_match_reply(
                    title=fuzzy.error.get_title(lang),
                    detected_text=question,
                    solution=fuzzy.error.get_solution(lang),
                    score=fuzzy.score,
                    lang=lang,
                )
                await _send_match_with_media(message, fuzzy.error, reply_text)
                mark_solved(chat_id, user.id)
                start_followup(message, lang)
                return
            ai_ans = await ai_answer_service.generate(question, errors, lang)
            if ai_ans:
                await message.reply(ai_ans.text)
                mark_solved(chat_id, user.id)
                start_followup(message, lang)
                return
            mentions = role_cache.get_support_mentions()
            mention_str = " ".join(mentions)
            if lang == "ru":
                await message.reply(
                    f"❓ Точного ответа не нашлось.\n"
                    + (f"{mention_str} — помогите!" if mention_str else "Обратитесь к администратору.")
                )
            else:
                await message.reply(
                    f"❓ Aniq javob topilmadi.\n"
                    + (f"{mention_str} — yordam bering!" if mention_str else "Administratorga murojaat qiling.")
                )
            return

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
                _delayed_reply(message, bot, lang, None, text, state_manager, "keyword")
            )
            _pending[(chat_id, user.id)] = task
        return

    result = await classify(text)
    lang = _lang(result.language)
    await _update_user_lang(user.id, user.username, lang)

    logger.info(
        f"[cls] user={user.id} chat={chat_id} mode={mode} "
        f"type={result.message_type} support={result.is_support_message} "
        f"conf={result.confidence:.2f} lang={lang}"
    )

    # ── 2a. Muammo hal bo'ldi yoki rahmat ────────────────────────────────────
    if result.message_type in ("resolved", "greeting") and result.confidence >= 0.6:
        if was_recently_solved(chat_id, user.id):
            # Bot yechgan edi → rahmat/ishladi javobiga munosabat bildirish
            await message.reply(random.choice(_GRATITUDE_REPLIES.get(lang, _GRATITUDE_REPLIES["uz"])))
            cancel_followup(chat_id, user.id)
            _solved_at.pop((chat_id, user.id), None)
            logger.info(f"[gratitude] chat={chat_id} user={user.id}")

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
        _delayed_reply(message, bot, lang, result, text, state_manager, "ai")
    )
    _pending[(chat_id, user.id)] = task
    logger.info(
        f"30s timer boshlandi (AI) — chat={chat_id} "
        f"conf={result.confidence:.2f} detail={result.has_enough_detail}"
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _send_match_with_media(message: Message, error: object, reply_text: str) -> None:
    """Yechim + video/rasm bitta xabarda (caption). Media yo'q bo'lsa faqat matn."""
    video_id = getattr(error, "solution_video_file_id", None)
    image_id = getattr(error, "solution_image_file_id", None)
    cap = reply_text[:1024]
    if video_id:
        try:
            await message.reply_video(video=video_id, caption=cap)
            return
        except Exception as exc:
            logger.warning(f"Video yuborishda xatolik: {exc}")
    if image_id:
        try:
            await message.reply_photo(photo=image_id, caption=cap)
            return
        except Exception as exc:
            logger.warning(f"Rasm yuborishda xatolik: {exc}")
    await message.reply(reply_text)


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
