from __future__ import annotations

import httpx
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from bot.i18n import t
from bot.keyboards import cancel_keyboard
from bot.services import translation_service
from bot.states import AddErrorStates, AddVideoStates
from config.logger import logger
from config.settings import settings
from database.connection import get_session
from database.repositories import ErrorRepository, UserRepository

router = Router(name="admin")


def _is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS


async def _get_lang(user_id: int, language_code: str | None = None) -> str:
    async with get_session() as session:
        user = await UserRepository(session).get(user_id)
        if user:
            return user.language
    return "ru" if language_code == "ru" else "uz"


# ── /cancel ───────────────────────────────────────────────────────────────────

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    lang = await _get_lang(message.from_user.id, message.from_user.language_code)
    current = await state.get_state()
    if current is None:
        await message.answer(t("cancel_no_state", lang), reply_markup=ReplyKeyboardRemove())
        return
    await state.clear()
    await message.answer(t("cancel_ok", lang), reply_markup=ReplyKeyboardRemove())


# ── /add_error — 2 bosqich + AI tarjima ──────────────────────────────────────

@router.message(Command("add_error"))
async def cmd_add_error(message: Message, state: FSMContext) -> None:
    lang = await _get_lang(message.from_user.id, message.from_user.language_code)
    if not _is_admin(message.from_user.id):
        await message.answer(t("add_error_admin_only", lang))
        return
    await state.set_state(AddErrorStates.waiting_for_title)
    await state.update_data(lang=lang)
    await message.answer(
        "📝 <b>1/2</b> — Xatolik nomini yuboring (istalgan tilda: uz yoki ru)",
        reply_markup=cancel_keyboard(),
    )


@router.message(AddErrorStates.waiting_for_title, F.text)
async def process_title(message: Message, state: FSMContext) -> None:
    title = message.text.strip()
    if len(title) < 3:
        await message.answer("❌ Nom juda qisqa. Kamida 3 ta belgi.")
        return
    await state.update_data(title=title)
    await state.set_state(AddErrorStates.waiting_for_solution)
    await message.answer(
        "💡 <b>2/2</b> — Yechimni yuboring:\n\n"
        "• Faqat matn\n"
        "• Rasm + caption (yechim matni)\n"
        "• Video + caption (yechim matni)\n\n"
        "<i>AI ikkinchi tilga avtomatik tarjima qiladi.</i>",
    )


@router.message(AddErrorStates.waiting_for_solution)
async def process_solution(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang: str = data.get("lang", "uz")
    title: str = data["title"]

    # Media va matn ajratish
    solution_text: str = ""
    video_file_id: str | None = None
    image_file_id: str | None = None

    if message.text:
        solution_text = message.text.strip()
    elif message.video:
        video_file_id = message.video.file_id
        solution_text = (message.caption or "").strip()
    elif message.photo:
        image_file_id = message.photo[-1].file_id
        solution_text = (message.caption or "").strip()
    elif message.document and message.document.mime_type and message.document.mime_type.startswith("video"):
        video_file_id = message.document.file_id
        solution_text = (message.caption or "").strip()

    if not solution_text:
        await message.answer(
            "❌ Yechim matni kerak.\n"
            "Video/rasmga <b>caption</b> qo'shing yoki faqat matn yuboring."
        )
        return

    # Tarjima
    wait_msg = await message.answer("🔄 AI tarjima qilmoqda...")

    translated = await translation_service.translate(title, solution_text)

    if translated is None:
        # Fallback — original matn ikki tilda ham
        title_ru = title_uz = title
        keywords = [title]
        solution_ru = solution_uz = solution_text
    else:
        title_ru    = translated.title_ru
        title_uz    = translated.title_uz
        keywords    = translated.keywords
        solution_ru = translated.solution_ru
        solution_uz = translated.solution_uz

    # DB ga saqlash
    try:
        async with get_session() as session:
            entry = await ErrorRepository(session).create(
                title=title_ru,
                keywords=keywords,
                solution=solution_ru,
                title_ru=title_ru,
                title_uz=title_uz,
                keywords_ru=keywords,
                keywords_uz=keywords,
                solution_ru=solution_ru,
                solution_uz=solution_uz,
                solution_video_file_id=video_file_id,
                solution_image_file_id=image_file_id,
            )
    except Exception as exc:
        logger.exception(f"add_error saqlashda xatolik: {exc}")
        await state.clear()
        await wait_msg.edit_text(t("add_error_save_error", lang))
        return

    await state.clear()
    logger.info(f"Yangi error qo'shildi id={entry.id} title_ru={title_ru!r}")

    media_mark = ""
    if video_file_id:
        media_mark = " 🎥"
    elif image_file_id:
        media_mark = " 🖼"

    kw_str = ", ".join(keywords[:5])
    await wait_msg.edit_text(
        f"✅ <b>Saqlandi{media_mark}</b>\n\n"
        f"<b>#{entry.id}</b>\n"
        f"🇷🇺 {title_ru}\n"
        f"🇺🇿 {title_uz}\n"
        f"🔑 {kw_str}{'…' if len(keywords) > 5 else ''}"
    )


@router.message(AddErrorStates.waiting_for_title)
async def fsm_title_wrong(message: Message, state: FSMContext) -> None:
    await message.answer("❌ Matn yuboring.")


# ── /add_video — mavjud xatolikka video qo'shish ─────────────────────────────

@router.message(Command("add_video"))
async def cmd_add_video(message: Message, state: FSMContext) -> None:
    lang = await _get_lang(message.from_user.id, message.from_user.language_code)
    if not _is_admin(message.from_user.id):
        await message.answer(t("add_error_admin_only", lang))
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        await message.answer(t("add_video_no_id", lang))
        return
    error_id = int(parts[1].strip())
    async with get_session() as session:
        entry = await ErrorRepository(session).get_by_id(error_id)
    if entry is None:
        await message.answer(
            t("add_video_not_found", lang).replace("#{id}", str(error_id))
        )
        return
    await state.set_state(AddVideoStates.waiting_for_video)
    await state.update_data(lang=lang, error_id=error_id)
    await message.answer(
        t("add_video_prompt", lang)
        .replace("#{id}", str(error_id))
        .replace("{title}", entry.get_title(lang)),
        reply_markup=cancel_keyboard(),
    )


@router.message(AddVideoStates.waiting_for_video, F.video)
async def process_video(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang: str = data.get("lang", "uz")
    error_id: int = data["error_id"]
    file_id = message.video.file_id
    try:
        async with get_session() as session:
            await ErrorRepository(session).update_video(error_id, file_id)
    except Exception as exc:
        logger.exception(f"Video saqlashda xatolik: {exc}")
        await state.clear()
        await message.answer(t("add_error_save_error", lang), reply_markup=ReplyKeyboardRemove())
        return
    await state.clear()
    logger.info(f"Video saqlandi: error_id={error_id} file_id={file_id[:20]}...")
    await message.answer(
        t("add_video_saved", lang).replace("#{id}", str(error_id)),
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(AddVideoStates.waiting_for_video)
async def fsm_video_wrong_input(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang: str = data.get("lang", "uz")
    await message.answer(t("add_video_not_video", lang))


# ── KB admin buyruqlari ───────────────────────────────────────────────────────

@router.message(Command("pending_kb"))
async def cmd_pending_kb(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        await message.answer("⛔️ Bu buyruq faqat adminlar uchun.")
        return
    if not settings.KB_API_URL or not settings.KB_API_KEY:
        await message.answer("⚠️ KB_API_URL yoki KB_API_KEY sozlanmagan.")
        return
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.KB_API_URL}/kb/entries",
                headers={"X-API-Key": settings.KB_API_KEY},
                params={"status_filter": "pending", "limit": 10},
            )
            resp.raise_for_status()
            entries = resp.json()
    except Exception as exc:
        await message.answer(f"⚠️ KB ga ulanib bo'lmadi: {exc}")
        return
    if not entries:
        await message.answer("✅ Pending KB yozuvlar yo'q.")
        return
    lines = ["📋 <b>Pending KB yozuvlar:</b>\n"]
    for e in entries:
        uid = e["id"]
        title = e.get("title") or "—"
        solution = (e.get("solution") or "")[:80]
        lines.append(
            f"🔸 <code>{uid[:8]}…</code>\n"
            f"   <b>{title}</b>\n"
            f"   {solution}{'…' if len(e.get('solution','')) > 80 else ''}\n"
            f"   /verify_kb {uid}\n"
        )
    await message.answer("\n".join(lines))


@router.message(Command("verify_kb"))
async def cmd_verify_kb(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        await message.answer("⛔️ Bu buyruq faqat adminlar uchun.")
        return
    if not settings.KB_API_URL or not settings.KB_API_KEY:
        await message.answer("⚠️ KB_API_URL yoki KB_API_KEY sozlanmagan.")
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("Foydalanish: /verify_kb <uuid>")
        return
    entry_id = parts[1].strip()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.patch(
                f"{settings.KB_API_URL}/kb/entries/{entry_id}/verify",
                headers={"X-API-Key": settings.KB_API_KEY},
                json={"verified_by": message.from_user.id},
            )
            resp.raise_for_status()
            entry = resp.json()
    except httpx.HTTPStatusError as exc:
        await message.answer(
            f"❌ Topilmadi: {entry_id}" if exc.response.status_code == 404
            else f"⚠️ Xatolik: {exc.response.status_code}"
        )
        return
    except Exception as exc:
        await message.answer(f"⚠️ KB ga ulanib bo'lmadi: {exc}")
        return
    logger.info(f"KB entry verified: {entry_id} by admin {message.from_user.id}")
    await message.answer(f"✅ Tasdiqlandi!\n<b>{entry.get('title', '—')}</b>\n<code>{entry_id}</code>")


@router.message(Command("reject_kb"))
async def cmd_reject_kb(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        await message.answer("⛔️ Bu buyruq faqat adminlar uchun.")
        return
    if not settings.KB_API_URL or not settings.KB_API_KEY:
        await message.answer("⚠️ KB_API_URL yoki KB_API_KEY sozlanmagan.")
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("Foydalanish: /reject_kb <uuid>")
        return
    entry_id = parts[1].strip()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.patch(
                f"{settings.KB_API_URL}/kb/entries/{entry_id}/reject",
                headers={"X-API-Key": settings.KB_API_KEY},
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        await message.answer(
            f"❌ Topilmadi: {entry_id}" if exc.response.status_code == 404
            else f"⚠️ Xatolik: {exc.response.status_code}"
        )
        return
    except Exception as exc:
        await message.answer(f"⚠️ KB ga ulanib bo'lmadi: {exc}")
        return
    logger.info(f"KB entry rejected: {entry_id} by admin {message.from_user.id}")
    await message.answer(f"🗑 Rad etildi: <code>{entry_id}</code>")
