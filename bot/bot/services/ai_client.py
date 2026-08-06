from __future__ import annotations

"""Unified AI client — Google Gemini (primary) yoki Anthropic (fallback)."""

import base64
from pathlib import Path

from config.logger import logger
from config.settings import settings

GEMINI_MODEL = "gemini-flash-lite-latest"

_anthropic_client = None


def _get_anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        _anthropic_client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _anthropic_client


async def complete(
    *,
    system: str,
    user: str,
    max_tokens: int = 128,
) -> str:
    """Text completion — Google Gemini yoki Anthropic."""
    if settings.active_ai == "google":
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            model = genai.GenerativeModel(
                GEMINI_MODEL,
                system_instruction=system,
            )
            response = await model.generate_content_async(
                user,
                generation_config={"max_output_tokens": max_tokens, "temperature": 0.1},
            )
            return response.text.strip()
        except Exception as exc:
            logger.warning(f"Gemini xatolik: {exc}")
            return ""

    if settings.active_ai == "anthropic":
        try:
            client = _get_anthropic()
            response = await client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=max_tokens,
                system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user}],
            )
            return response.content[0].text.strip()
        except Exception as exc:
            logger.warning(f"Anthropic xatolik: {exc}")
            return ""

    return ""


async def vision_complete(
    *,
    system: str,
    user_text: str,
    image_path: Path,
    max_tokens: int = 256,
) -> str:
    """Vision (rasm + matn) completion."""
    if settings.active_ai == "google":
        try:
            import PIL.Image
            import google.generativeai as genai
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            model = genai.GenerativeModel(
                GEMINI_MODEL,
                system_instruction=system,
            )
            img = PIL.Image.open(image_path)
            response = await model.generate_content_async(
                [user_text, img],
                generation_config={"max_output_tokens": max_tokens, "temperature": 0.1},
            )
            return response.text.strip()
        except Exception as exc:
            logger.warning(f"Gemini vision xatolik: {exc}")
            return ""

    if settings.active_ai == "anthropic":
        try:
            suffix = image_path.suffix.lower()
            media_type = "image/png" if suffix == ".png" else "image/jpeg"
            image_data = base64.standard_b64encode(image_path.read_bytes()).decode()
            client = _get_anthropic()
            response = await client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=max_tokens,
                system=system,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
                        {"type": "text", "text": user_text},
                    ],
                }],
            )
            return response.content[0].text.strip()
        except Exception as exc:
            logger.warning(f"Anthropic vision xatolik: {exc}")
            return ""

    return ""
