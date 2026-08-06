from __future__ import annotations

from aiogram import Bot, Router
from aiogram.filters import IS_MEMBER, IS_NOT_MEMBER, ChatMemberUpdatedFilter
from aiogram.types import (
    CallbackQuery,
    ChatMemberUpdated,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from bot import group_cache, role_cache
from config.logger import logger
from config.settings import settings
from database.connection import get_session
from database.repositories import GroupRepository

router = Router(name="chat_member")

_GROUP_TYPES = {"group", "supergroup"}


def _approval_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Tasdiqlash",
                    callback_data=f"grp_approve:{chat_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Rad etish",
                    callback_data=f"grp_reject:{chat_id}",
                ),
            ]
        ]
    )


def _group_info_text(group, added_by) -> str:
    chat_id    = group.chat_id
    title      = group.title or "—"
    username   = f"@{group.username}" if group.username else "—"
    chat_type  = group.chat_type or "—"

    by_name     = group.added_by_name or "—"
    by_username = f"@{group.added_by_username}" if group.added_by_username else "—"
    by_id       = group.added_by_id or "—"

    return (
        f"🔔 <b>Yangi guruh so'rovi</b>\n\n"
        f"📋 <b>Guruh ma'lumotlari:</b>\n"
        f"• Nomi: <b>{title}</b>\n"
        f"• ID: <code>{chat_id}</code>\n"
        f"• Username: {username}\n"
        f"• Turi: {chat_type}\n\n"
        f"👤 <b>Kim qo'shdi:</b>\n"
        f"• Ism: <b>{by_name}</b>\n"
        f"• Username: {by_username}\n"
        f"• ID: <code>{by_id}</code>\n\n"
        f"Botni ushbu guruhda ishlashiga ruxsat berasizmi?"
    )


# ── Bot guruhga qo'shildi ─────────────────────────────────────────────────────

@router.my_chat_member(
    ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER),
)
async def bot_added_to_group(event: ChatMemberUpdated, bot: Bot) -> None:
    if event.chat.type not in _GROUP_TYPES:
        return

    chat    = event.chat
    from_u  = event.from_user

    full_name = " ".join(filter(None, [from_u.first_name, from_u.last_name])) if from_u else None

    async with get_session() as session:
        group = await GroupRepository(session).upsert(
            chat_id=chat.id,
            title=chat.title,
            username=chat.username,
            chat_type=chat.type,
            added_by_id=from_u.id if from_u else None,
            added_by_name=full_name,
            added_by_username=from_u.username if from_u else None,
        )

    logger.info(
        f"Bot guruhga qo'shildi: chat_id={chat.id} title={chat.title!r} "
        f"by={from_u.id if from_u else '?'}"
    )

    text = _group_info_text(group, from_u)
    kb   = _approval_keyboard(chat.id)

    for admin_id in settings.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, reply_markup=kb)
        except Exception as exc:
            logger.warning(f"Adminga xabar yuborilmadi ({admin_id}): {exc}")


# ── Bot guruhdan chiqarildi ───────────────────────────────────────────────────

@router.my_chat_member(
    ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER),
)
async def bot_removed_from_group(event: ChatMemberUpdated, bot: Bot) -> None:
    if event.chat.type not in _GROUP_TYPES:
        return

    chat_id = event.chat.id
    group_cache.mark_removed(chat_id)
    logger.info(f"Bot guruhdan chiqarildi: chat_id={chat_id}")


# ── Admin: Tasdiqlash ─────────────────────────────────────────────────────────

@router.callback_query(lambda c: c.data and c.data.startswith("grp_approve:"))
async def cb_approve_group(callback: CallbackQuery, bot: Bot) -> None:
    if callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("⛔️ Ruxsat yo'q", show_alert=True)
        return

    chat_id = int(callback.data.split(":")[1])

    async with get_session() as session:
        group = await GroupRepository(session).approve(chat_id, callback.from_user.id)

    if group is None:
        await callback.answer("❌ Guruh topilmadi", show_alert=True)
        return

    group_cache.mark_approved(chat_id)
    role_cache.set_active(chat_id)  # tasdiqlash = darhol active rejim
    logger.info(f"Guruh tasdiqlandi va active: chat_id={chat_id} by={callback.from_user.id}")

    title = group.title or str(chat_id)
    await callback.message.edit_text(
        f"✅ <b>Tasdiqlandi!</b>\n\n"
        f"Guruh: <b>{title}</b>\n"
        f"ID: <code>{chat_id}</code>\n"
        f"Admin: {callback.from_user.full_name}",
    )

    try:
        await bot.send_message(
            chat_id,
            "✅ <b>Bot ushbu guruhda ishlash uchun tasdiqlandi!</b>\n\n"
            "Screenshot yuboring — men xatolikni aniqlab, yechim topib beraman.",
        )
    except Exception as exc:
        logger.warning(f"Guruhga xush kelibsiz xabari yuborilmadi: {exc}")

    await callback.answer("✅ Tasdiqlandi!")


# ── Admin: Rad etish ──────────────────────────────────────────────────────────

@router.callback_query(lambda c: c.data and c.data.startswith("grp_reject:"))
async def cb_reject_group(callback: CallbackQuery, bot: Bot) -> None:
    if callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("⛔️ Ruxsat yo'q", show_alert=True)
        return

    chat_id = int(callback.data.split(":")[1])

    async with get_session() as session:
        group = await GroupRepository(session).reject(chat_id, callback.from_user.id)

    if group is None:
        await callback.answer("❌ Guruh topilmadi", show_alert=True)
        return

    group_cache.mark_removed(chat_id)
    logger.info(f"Guruh rad etildi: chat_id={chat_id} by={callback.from_user.id}")

    title = group.title or str(chat_id)
    await callback.message.edit_text(
        f"🚫 <b>Rad etildi</b>\n\n"
        f"Guruh: <b>{title}</b>\n"
        f"ID: <code>{chat_id}</code>",
    )

    try:
        await bot.send_message(
            chat_id,
            "🚫 Bot ushbu guruhda ishlash uchun ruxsat berilmadi.",
        )
        await bot.leave_chat(chat_id)
    except Exception as exc:
        logger.warning(f"Guruhdan chiqishda xatolik: {exc}")

    await callback.answer("🚫 Rad etildi!")
