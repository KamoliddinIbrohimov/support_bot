from __future__ import annotations

from datetime import datetime
from pathlib import Path

from config.settings import settings


def build_image_path(chat_id: int, user_id: int, ext: str = "jpg") -> Path:
    """Vaqt bilan noyob fayl yo'lini yasaydi."""
    now = datetime.utcnow()
    day_dir = settings.image_storage_dir / now.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)

    timestamp = now.strftime("%H%M%S_%f")
    filename = f"{chat_id}_{user_id}_{timestamp}.{ext.lstrip('.')}"
    return day_dir / filename
