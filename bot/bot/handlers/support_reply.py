from __future__ import annotations

"""Support-reply learning handler.

When a support agent replies to the bot's "not found" message,
this handler captures it and submits to KB as a pending entry.
"""

from aiogram import F, Router
from aiogram.types import Message

from bot import bot_context
from bot.services import kb_client
from bot.state_manager import StateManager
from config.logger import logger

router = Router(name="support_reply")

_GROUP_TYPES = {"group", "supergroup"}


@router.message(
    F.chat.type.in_(_GROUP_TYPES),
    F.reply_to_message.as_("replied_to"),
)
async def handle_support_reply(
    message: Message,
    replied_to: Message,
    state_manager: StateManager,
) -> None:
    """Capture support staff's reply to bot's 'not found' response."""
    # Only interested in replies to bot's own messages
    if not replied_to.from_user or replied_to.from_user.id != bot_context.bot_id:
        return

    # Only text replies are useful for learning
    if not message.text or len(message.text.strip()) < 5:
        return

    # Check if this bot message was a "not found" response we're watching
    watch = await state_manager.get_no_match_watch(
        bot_message_id=replied_to.message_id,
        chat_id=message.chat.id,
    )
    if watch is None:
        return

    # Found a support reply — submit to KB as pending
    ocr_text: str = watch.get("ocr_text", "")
    lang: str = watch.get("lang", "uz")
    solution: str = message.text.strip()

    logger.info(
        f"Support reply captured: user={message.from_user.id} "
        f"chat={message.chat.id} solution_len={len(solution)}"
    )

    submitted = await kb_client.submit_learned(
        query=ocr_text,
        solution=solution,
        language=lang,
        title=ocr_text[:80] if ocr_text else None,
    )

    if submitted:
        await state_manager.clear_no_match_watch(
            bot_message_id=replied_to.message_id,
            chat_id=message.chat.id,
        )
        # Silent confirmation — no group spam, just log
        logger.info("KB: new pending entry from support reply submitted")
