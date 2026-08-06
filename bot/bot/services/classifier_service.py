from __future__ import annotations

import json
from dataclasses import dataclass, field

from bot.services.ai_client import complete
from config.logger import logger
from config.settings import settings

_SYSTEM = (
    "You classify a message from a Telegram support group chat.\n"
    "The group has two types of people: support staff and clients.\n\n"
    "Determine:\n"
    "- language: uz | ru | other\n"
    "- message_type: one of:\n"
    "    'help_request'  — client asking for help, reporting a problem or error\n"
    "    'solution'      — someone providing a fix, instructions, or resolution\n"
    "    'resolved'      — client confirms the problem is now fixed "
    "('ishladi', 'hal bo\\'ldi', 'работает', 'решилось', 'ok rahmat', 'спасибо помогло' etc.)\n"
    "    'greeting'      — hello, congratulations, holiday wishes, casual friendly message\n"
    "    'informational' — announcement, warning, FYI, staff coordination, system notice\n"
    "    'other'         — anything else (chitchat, unrelated)\n"
    "- is_support_message: true if the message style suggests support staff "
    "(giving solutions, instructions, technical guidance, professional tone). "
    "false if it looks like a client (asking, complaining, describing a problem).\n"
    "- has_enough_detail: true only if message_type is 'help_request' AND there is enough "
    "information to act (specific error description, or image mentioned).\n"
    "- confidence: float 0.0–1.0 of how confident you are in message_type.\n\n"
    "Respond with JSON only, no extra text:\n"
    '{"language":"uz","message_type":"other","is_support_message":false,'
    '"has_enough_detail":false,"confidence":0.0}'
)

_FALLBACK = {
    "language": "uz",
    "message_type": "other",
    "is_support_message": False,
    "has_enough_detail": False,
    "confidence": 0.0,
}

_VALID_TYPES = {"help_request", "solution", "resolved", "greeting", "informational", "other"}


@dataclass(slots=True)
class ClassifyResult:
    language: str
    message_type: str
    is_support_message: bool
    has_enough_detail: bool
    confidence: float

    @property
    def is_help_request(self) -> bool:
        return self.message_type == "help_request"


async def classify(text: str) -> ClassifyResult:
    if not settings.llm_enabled or not text.strip():
        return ClassifyResult(**_FALLBACK)

    raw = await complete(system=_SYSTEM, user=text[:1000], max_tokens=120)
    if not raw:
        return ClassifyResult(**_FALLBACK)

    try:
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        data = json.loads(raw)
        lang = data.get("language", "uz")
        if lang not in ("uz", "ru", "other"):
            lang = "uz"
        msg_type = data.get("message_type", "other")
        if msg_type not in _VALID_TYPES:
            msg_type = "other"
        return ClassifyResult(
            language=lang,
            message_type=msg_type,
            is_support_message=bool(data.get("is_support_message", False)),
            has_enough_detail=bool(data.get("has_enough_detail", False)),
            confidence=float(data.get("confidence", 0.0)),
        )
    except Exception as exc:
        logger.warning(f"Classifier parse xatolik: {exc} | raw={raw!r}")
        return ClassifyResult(**_FALLBACK)
