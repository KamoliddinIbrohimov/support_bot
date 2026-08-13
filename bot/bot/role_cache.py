"""Cross-group role detection and per-group mode management.

Per-group per-user roles:
  Each group tracks its own user roles independently.
  A user can be 'plugin_staff' in one group and 'customer' in another.
  Roles are loaded from DB at startup and updated in real-time as the bot
  observes messages.

Per-group mode (set by admin, persisted in DB):
  'learning'  — bot only observes: learns roles, never responds to clients
  'knowledge' — full flow: KB → AI → support escalation (30s delay)
  'express'   — immediate flow: KB → AI → support escalation (no delay)
"""

from __future__ import annotations

from config.logger import logger

VALID_MODES = {"learning", "knowledge", "express"}
DEFAULT_MODE = "knowledge"

# Per-group per-user roles: (chat_id, user_id) → {role, username, full_name}
_user_roles: dict[tuple[int, int], dict] = {}

# Per-group mode: chat_id → mode string
_group_mode: dict[int, str] = {}


# ── Role detection ─────────────────────────────────────────────────────────────

SUPPORT_ROLES = {"plugin_staff", "communicator", "poster_staff"}

def is_support(chat_id: int, user_id: int) -> bool:
    entry = _user_roles.get((chat_id, user_id))
    return entry is not None and entry["role"] in SUPPORT_ROLES


def get_user_role(chat_id: int, user_id: int) -> str | None:
    entry = _user_roles.get((chat_id, user_id))
    return entry["role"] if entry else None


def set_user_role(
    chat_id: int,
    user_id: int,
    role: str,
    username: str | None = None,
    full_name: str | None = None,
) -> bool:
    """Set role for a user in a specific group. Returns True if role changed."""
    key = (chat_id, user_id)
    current = _user_roles.get(key, {})
    old_role = current.get("role")

    _user_roles[key] = {
        "role": role,
        "username": username or current.get("username"),
        "full_name": full_name or current.get("full_name"),
    }

    changed = old_role != role
    if changed:
        logger.info(f"[role-change] chat={chat_id} user={user_id} {old_role} → {role}")
    return changed


def load_roles(chat_id: int, roles: list) -> None:
    """Load roles from DB records for a group at startup."""
    for r in roles:
        _user_roles[(chat_id, r.telegram_user_id)] = {
            "role": r.role,
            "username": r.username,
            "full_name": r.full_name,
        }


def get_support_mentions(chat_id: int) -> list[str]:
    """@username list of support users in this specific group (max 5)."""
    mentions = []
    for (gid, _uid), info in _user_roles.items():
        if gid == chat_id and info["role"] in SUPPORT_ROLES:
            uname = info.get("username")
            if uname:
                mentions.append(f"@{uname}")
    return mentions[:5]


def support_count(chat_id: int) -> int:
    return sum(
        1 for (gid, _), info in _user_roles.items()
        if gid == chat_id and info["role"] == "plugin_staff"
    )


# ── Group mode ─────────────────────────────────────────────────────────────────

def get_mode(chat_id: int) -> str:
    return _group_mode.get(chat_id, DEFAULT_MODE)


def set_mode(chat_id: int, mode: str) -> None:
    if mode not in VALID_MODES:
        mode = DEFAULT_MODE
    _group_mode[chat_id] = mode
    logger.info(f"[role-mode] chat={chat_id} → {mode}")


def remove_mode(chat_id: int) -> None:
    _group_mode.pop(chat_id, None)
