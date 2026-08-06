"""Translate a support entry (title + solution) to both ru and uz, auto-generate keywords.

Input: title and solution in any language (uz, ru, or mixed).
Output: TranslatedEntry with both language versions + keyword list.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from bot.services.ai_client import complete
from config.logger import logger

_SYSTEM = """\
You are a knowledge-base assistant for an Uzbekistan POS / fiscal system support team.

Input: a problem title and its solution text (in Uzbek, Russian, or mixed).
Your task:
1. Translate/rewrite BOTH title and solution to Russian AND Uzbek
2. Generate 6-10 search keywords covering both languages

Output a JSON object:
{
  "title_ru":    "...",   // problem title in Russian (max 100 chars)
  "title_uz":    "...",   // problem title in Uzbek (max 100 chars)
  "keywords":    "...",   // comma-separated keywords in Russian and Uzbek mixed
  "solution_ru": "...",   // complete solution in Russian
  "solution_uz": "..."    // complete solution in Uzbek
}

Rules:
- Keep solutions complete and clear; use step-by-step format if applicable
- keywords must include the main error terms in BOTH languages
- Respond with JSON only, no markdown, no extra text
"""


@dataclass
class TranslatedEntry:
    title_ru: str
    title_uz: str
    keywords: list[str]
    solution_ru: str
    solution_uz: str


async def translate(title: str, solution: str) -> TranslatedEntry | None:
    prompt = f"Title: {title}\nSolution: {solution}"

    raw = await complete(system=_SYSTEM, user=prompt[:2500], max_tokens=800)
    if not raw:
        return None

    raw = raw.strip()
    try:
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        data = json.loads(raw)

        kw_str = str(data.get("keywords", ""))
        kw_list = [k.strip() for k in kw_str.split(",") if k.strip()]
        if not kw_list:
            kw_list = [title]

        return TranslatedEntry(
            title_ru=str(data.get("title_ru", title)).strip()[:100],
            title_uz=str(data.get("title_uz", title)).strip()[:100],
            keywords=kw_list,
            solution_ru=str(data.get("solution_ru", solution)).strip(),
            solution_uz=str(data.get("solution_uz", solution)).strip(),
        )
    except Exception as exc:
        logger.warning(f"Translation parse xatolik: {exc} | raw={raw[:200]!r}")
        return None
