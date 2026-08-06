from __future__ import annotations

"""Knowledge Base API client — semantic search before LLM pipeline."""

import asyncio
from dataclasses import dataclass
from typing import Any

from config.logger import logger
from config.settings import settings


@dataclass
class KBMatch:
    entry_id: str
    title: str | None
    solution: str
    similarity: float
    language: str | None


async def search(query: str, lang: str = "uz") -> KBMatch | None:
    """Query KB service for a semantic match.

    Returns the best match if similarity >= threshold, else None.
    """
    if not settings.KB_API_URL or not settings.KB_API_KEY:
        return None

    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{settings.KB_API_URL}/kb/search",
                headers={"X-API-Key": settings.KB_API_KEY},
                json={
                    "query": query[:1500],
                    "threshold": settings.KB_SIMILARITY_THRESHOLD,
                    "limit": 1,
                },
            )
            response.raise_for_status()
            data = response.json()

        if not data.get("found") or not data.get("results"):
            return None

        best = data["results"][0]
        entry = best["entry"]
        return KBMatch(
            entry_id=entry["id"],
            title=entry.get("title"),
            solution=entry["solution"],
            similarity=best["similarity"],
            language=entry.get("language"),
        )
    except Exception as exc:
        logger.warning(f"KB search failed: {exc}")
        return None


async def submit_learned(
    *,
    query: str,
    solution: str,
    language: str | None = None,
    title: str | None = None,
) -> bool:
    """Submit a support-staff reply as a new pending KB entry."""
    if not settings.KB_API_URL or not settings.KB_API_KEY:
        return False

    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{settings.KB_API_URL}/kb/entries",
                headers={"X-API-Key": settings.KB_API_KEY},
                json={
                    "title": title,
                    "description": query[:500],
                    "solution": solution,
                    "language": language,
                    "source": "learned_from_support",
                    "status": "pending",
                },
            )
            response.raise_for_status()
        logger.info("KB: support reply submitted as pending entry")
        return True
    except Exception as exc:
        logger.warning(f"KB submit failed: {exc}")
        return False
