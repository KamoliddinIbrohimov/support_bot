"""AI-based OCR — Gemini/Anthropic Vision orqali rasm matnini o'qiydi."""
from __future__ import annotations

from pathlib import Path

from bot.services.ai_client import vision_complete
from config.logger import logger
from config.settings import settings


async def claude_ocr(image_path: str | Path) -> str:
    """AI Vision orqali rasm matnini o'qiydi."""
    if not settings.vision_enabled:
        return ""
    result = await vision_complete(
        system="You extract text from images exactly as written.",
        user_text=(
            "Extract ALL visible text from this image exactly as written. "
            "Include error messages, dialog boxes, status bars, corner notifications, "
            "and any text anywhere in the image. "
            "Return only the extracted text, nothing else."
        ),
        image_path=Path(image_path),
        max_tokens=600,
    )
    if result:
        logger.info(f"AI OCR: {len(result)} chars extracted")
    return result or ""
