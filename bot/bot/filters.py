from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import Message

from bot import bot_context


class IsGroupMentionOrReply(BaseFilter):
    """True when a group text message is a reply to the bot OR mentions the bot."""

    async def __call__(self, message: Message) -> bool:
        # Reply to one of the bot's messages
        if (
            message.reply_to_message
            and message.reply_to_message.from_user
            and message.reply_to_message.from_user.id == bot_context.bot_id
        ):
            return True

        # @mention in text
        if message.entities and message.text and bot_context.bot_username:
            for entity in message.entities:
                if entity.type == "mention":
                    mention = message.text[entity.offset : entity.offset + entity.length]
                    if mention.lstrip("@").lower() == bot_context.bot_username.lower():
                        return True

        return False
