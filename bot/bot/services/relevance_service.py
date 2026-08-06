from __future__ import annotations

import json
import re

from bot.services.ai_client import complete
from config.logger import logger
from config.settings import settings

# POS/fiskal tizimga aloqador kalit so'zlar — agar topilsa, AI chaqirilmaydi
_RELEVANT_RE = re.compile(
    r"\b("
    # Rus
    r"ошибк[аи]|сбой|не\s+работает|чек|принтер|терминал|касс[аы]|фискал"
    r"|оффлайн|подключени[ею]|соединени[ею]|интернет|сеть|сервер"
    r"|error|fail|crash|receipt|printer|terminal|fiscal|offline|connection"
    # O'zbek
    r"|xato|ishlamayapti|chek|printer|terminal|kassa|fiskal"
    r"|oflayn|ulanmayapti|nosozlik|muammo|tarmoq|internet|server"
    r")\b",
    re.IGNORECASE,
)


async def check_relevance(*, ocr_text: str = "", user_text: str = "") -> bool:
    combined = " ".join(filter(None, [user_text, ocr_text])).strip()
    if not combined:
        return True

    # Agar taniqli POS kalit so'z topilsa — AI ga murojaat qilmasdan True
    if _RELEVANT_RE.search(combined):
        logger.debug("Relevance: keyword hit → relevant (AI skipped)")
        return True

    if not settings.llm_enabled:
        return True

    system = (
        "You are a relevance checker for a technical support bot. "
        f"The bot covers: {settings.PRODUCT_DOMAIN} "
        "Given a customer message and/or OCR text from a screenshot, "
        "decide if the issue is related to this system. "
        'Respond with JSON only: {"is_relevant": true}'
    )

    raw = await complete(system=system, user=combined[:1200], max_tokens=20)
    if not raw:
        return True

    try:
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        return bool(json.loads(raw).get("is_relevant", True))
    except Exception as exc:
        logger.warning(f"Relevance parse xatolik: {exc}")
        return True
