"""Cross-group role detection and per-group mode management.

Global support cache: once a user is identified as support in ANY group,
they are treated as support in ALL groups (cross-group knowledge transfer).

Per-group mode:
  'observing' — bot reads every message, learns roles, never responds
  'active'    — bot responds to clients normally

Activation triggers (observing → active):
  1. A globally-known support user sends a message in this group
  2. AI classifies a message as 'solution' / is_support_message=True
"""

from __future__ import annotations

from config.logger import logger

# Global: user_id → {username, full_name}
_global_support: dict[int, dict[str, str | None]] = {}

# Per-group mode
_group_mode: dict[int, str] = {}  # chat_id → "observing" | "active"


# ── Support detection ──────────────────────────────────────────────────────────

def is_support(user_id: int) -> bool:
    return user_id in _global_support


def mark_support(
    user_id: int,
    username: str | None = None,
    full_name: str | None = None,
) -> None:
    if user_id not in _global_support:
        _global_support[user_id] = {"username": username, "full_name": full_name}
    else:
        if username:
            _global_support[user_id]["username"] = username
        if full_name:
            _global_support[user_id]["full_name"] = full_name


def get_support_mentions() -> list[str]:
    """@username ko'rinishidagi support ro'yxati (max 5)."""
    mentions = []
    for info in _global_support.values():
        uname = info.get("username")
        if uname:
            mentions.append(f"@{uname}")
    return mentions[:5]


def support_count() -> int:
    return len(_global_support)


# ── Group mode ─────────────────────────────────────────────────────────────────

def get_mode(chat_id: int) -> str:
    return _group_mode.get(chat_id, "observing")


def set_active(chat_id: int) -> None:
    _group_mode[chat_id] = "active"


def try_activate(chat_id: int, reason: str) -> bool:
    """Activate group if not already active. Returns True on first activation."""
    if get_mode(chat_id) == "active":
        return False
    _group_mode[chat_id] = "active"
    logger.info(f"[role-activate] chat={chat_id} — {reason}")
    return True
