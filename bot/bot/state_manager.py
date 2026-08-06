from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from time import time

from redis.asyncio import Redis

from config.settings import settings


@dataclass
class ConvState:
    status: str        # "idle" | "waiting_for_screenshot"
    language: str      # "uz" | "ru" | "other"
    ts: float = 0.0    # unix timestamp of last update


class StateManager:
    """Per-user, per-chat conversation state backed by Redis."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _key(self, user_id: int, chat_id: int) -> str:
        return f"conv_state:{user_id}:{chat_id}"

    async def get(self, user_id: int, chat_id: int) -> ConvState | None:
        raw = await self._redis.get(self._key(user_id, chat_id))
        if raw is None:
            return None
        data = json.loads(raw)
        return ConvState(**data)

    async def set_waiting(self, user_id: int, chat_id: int, language: str) -> None:
        state = ConvState(status="waiting_for_screenshot", language=language, ts=time())
        await self._redis.setex(
            self._key(user_id, chat_id),
            settings.CONV_STATE_TTL,
            json.dumps(asdict(state)),
        )

    async def clear(self, user_id: int, chat_id: int) -> None:
        await self._redis.delete(self._key(user_id, chat_id))

    # ── No-match watch (support-reply learning) ───────────────────────────────

    def _watch_key(self, bot_message_id: int, chat_id: int) -> str:
        return f"no_match_watch:{chat_id}:{bot_message_id}"

    async def set_no_match_watch(
        self,
        *,
        bot_message_id: int,
        chat_id: int,
        ocr_text: str,
        lang: str,
    ) -> None:
        """Store bot's 'not found' message so we can capture the support reply."""
        data = json.dumps({"ocr_text": ocr_text[:500], "lang": lang})
        await self._redis.setex(
            self._watch_key(bot_message_id, chat_id),
            86400,  # 24h TTL
            data,
        )

    async def get_no_match_watch(
        self, bot_message_id: int, chat_id: int
    ) -> dict | None:
        raw = await self._redis.get(self._watch_key(bot_message_id, chat_id))
        if raw is None:
            return None
        return json.loads(raw)

    async def clear_no_match_watch(self, bot_message_id: int, chat_id: int) -> None:
        await self._redis.delete(self._watch_key(bot_message_id, chat_id))
