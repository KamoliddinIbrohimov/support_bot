"""Tracks active support conversations to auto-extract solutions.

Flow:
1. Bot @mentions support (no KB answer found for client's problem)
2. All subsequent messages in that chat are collected (TrackedMsg)
3. After INACTIVITY_SECS of silence → registered callback is fired
4. Callback (resolution_handler) analyzes with AI and saves to DB

Only group chats are tracked.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Awaitable, Callable

INACTIVITY_SECS = 300  # 5 min silence → analyze
MIN_MESSAGES = 3        # analysis requires at least 3 messages (client + support)

_Callback = Callable[[int, list["TrackedMsg"]], Awaitable[None]]


@dataclass
class TrackedMsg:
    user_id: int
    username: str | None
    display_name: str
    is_support: bool
    text: str
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class _Convo:
    chat_id: int
    messages: list[TrackedMsg] = field(default_factory=list)
    _task: asyncio.Task | None = field(default=None, repr=False)


_active: dict[int, _Convo] = {}
_callback: _Callback | None = None


def set_callback(cb: _Callback) -> None:
    global _callback
    _callback = cb


def is_tracking(chat_id: int) -> bool:
    return chat_id in _active


def start(chat_id: int, initial: TrackedMsg) -> None:
    """Begin tracking a new conversation (or append if already tracking)."""
    if chat_id in _active:
        add(chat_id, initial)
        return
    _active[chat_id] = _Convo(chat_id=chat_id, messages=[initial])
    _reset_timer(chat_id)


def add(chat_id: int, msg: TrackedMsg) -> None:
    """Append a message and reset the inactivity timer."""
    if chat_id not in _active:
        return
    _active[chat_id].messages.append(msg)
    _reset_timer(chat_id)


def stop(chat_id: int) -> None:
    """Cancel tracking without triggering analysis."""
    convo = _active.pop(chat_id, None)
    if convo and convo._task and not convo._task.done():
        convo._task.cancel()


def stop_and_get(chat_id: int) -> list[TrackedMsg]:
    """Stop tracking immediately and return collected messages (for early resolution)."""
    convo = _active.pop(chat_id, None)
    if not convo:
        return []
    if convo._task and not convo._task.done():
        convo._task.cancel()
    return convo.messages


def _reset_timer(chat_id: int) -> None:
    convo = _active.get(chat_id)
    if not convo:
        return
    if convo._task and not convo._task.done():
        convo._task.cancel()
    convo._task = asyncio.create_task(_inactivity_fire(chat_id))


async def _inactivity_fire(chat_id: int) -> None:
    try:
        await asyncio.sleep(INACTIVITY_SECS)
        convo = _active.pop(chat_id, None)
        if convo and _callback and len(convo.messages) >= MIN_MESSAGES:
            await _callback(chat_id, convo.messages)
    except asyncio.CancelledError:
        pass
