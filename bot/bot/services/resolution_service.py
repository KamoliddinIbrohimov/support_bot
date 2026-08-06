"""Analyze a finished support conversation and extract a reusable KB entry.

Sends the conversation transcript to Claude, gets back:
  title_ru, title_uz, keywords, solution_ru, solution_uz

Returns None if the conversation contains no clear resolution.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from bot.services.ai_client import complete
from config.logger import logger

_SYSTEM = """\
You are a knowledge-base assistant for a Uzbekistan POS / fiscal system support team.

A Telegram group conversation is given below (between support staff and a client).
Your task: extract a reusable knowledge-base entry from this conversation.

Output a JSON object with these fields:
  "title_ru"    — short problem title in Russian (max 80 chars)
  "title_uz"    — short problem title in Uzbek (max 80 chars)
  "keywords"    — 5–10 comma-separated keywords in Russian and Uzbek mixed
  "solution_ru" — complete step-by-step solution in Russian
  "solution_uz" — complete step-by-step solution in Uzbek

Rules:
- If the conversation does NOT contain a clear resolution, output: null
- Do not invent solutions; extract only what was actually discussed
- Keep solutions concise but complete (max 500 chars each)
- keywords must include both Russian and Uzbek variants of the main terms

Respond with JSON only, no markdown, no extra text.
"""


@dataclass
class ResolvedEntry:
    title_ru: str
    title_uz: str
    keywords: str
    solution_ru: str
    solution_uz: str


async def analyze(messages: list) -> ResolvedEntry | None:
    if len(messages) < 3:
        return None

    lines: list[str] = []
    for msg in messages:
        role = "[Support]" if msg.is_support else "[Mijoz/Client]"
        name = msg.display_name or str(msg.user_id)
        lines.append(f"{role} {name}: {msg.text}")

    transcript = "\n".join(lines)[:4000]

    raw = await complete(system=_SYSTEM, user=transcript, max_tokens=700)
    if not raw:
        return None

    raw = raw.strip()
    if raw == "null" or raw == "":
        return None

    try:
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        data = json.loads(raw)
        if not data:
            return None

        title_ru = str(data.get("title_ru", "")).strip()[:80]
        title_uz = str(data.get("title_uz", "")).strip()[:80]
        solution_ru = str(data.get("solution_ru", "")).strip()
        solution_uz = str(data.get("solution_uz", "")).strip()
        keywords = str(data.get("keywords", "")).strip()

        if not title_ru or not solution_ru:
            return None

        return ResolvedEntry(
            title_ru=title_ru,
            title_uz=title_uz or title_ru,
            keywords=keywords,
            solution_ru=solution_ru,
            solution_uz=solution_uz or solution_ru,
        )
    except Exception as exc:
        logger.warning(f"Resolution parse xatolik: {exc} | raw={raw[:200]!r}")
        return None
