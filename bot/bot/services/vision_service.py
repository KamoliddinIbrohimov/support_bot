from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from bot.services.ai_client import vision_complete
from config.logger import logger
from config.settings import settings
from database.models import ErrorEntry

_rate_counts: dict[int, dict[str, int]] = defaultdict(dict)


def _is_rate_limited(user_id: int) -> bool:
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    return _rate_counts[user_id].get(today, 0) >= settings.VISION_DAILY_LIMIT_PER_USER


def _increment_rate(user_id: int) -> None:
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    _rate_counts[user_id][today] = _rate_counts[user_id].get(today, 0) + 1


class VisionMatchResult:
    __slots__ = ("error", "score")

    def __init__(self, error: ErrorEntry, score: float = 100.0) -> None:
        self.error = error
        self.score = score


async def identify_error(
    *,
    image_path: Path,
    ocr_text: str,
    errors: Sequence[ErrorEntry],
    lang: str,
    user_id: int,
) -> VisionMatchResult | None:
    if not settings.vision_enabled or not errors:
        return None

    if _is_rate_limited(user_id):
        logger.info(f"Vision rate limit: user={user_id}")
        return None

    catalog = "\n".join(
        f"ID={e.id}: {e.get_title(lang)}"
        + (f" — {e.get_description(lang)}" if e.get_description(lang) else "")
        for e in errors
    )

    system = (
        "You are a technical support assistant. "
        "Look at the screenshot and the OCR text to identify the error. "
        "Reply with ONLY the integer ID from the list, or 'none'."
    )
    user_text = (
        f"OCR text: '{ocr_text or '(none)'}'\n\n"
        f"Known errors:\n{catalog}\n\n"
        "Which error ID matches? Reply with ONLY the integer or 'none'."
    )

    raw = await vision_complete(
        system=system,
        user_text=user_text,
        image_path=image_path,
        max_tokens=16,
    )

    if not raw or raw.lower() == "none":
        return None

    try:
        error_id = int(raw.strip())
    except ValueError:
        logger.warning(f"Vision unexpected response: {raw!r}")
        return None

    matched = next((e for e in errors if e.id == error_id), None)
    if matched:
        _increment_rate(user_id)
    return VisionMatchResult(error=matched) if matched else None
