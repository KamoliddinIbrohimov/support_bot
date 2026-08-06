from __future__ import annotations

import asyncio
from functools import partial

from config.logger import logger
from config.settings import settings

EMBEDDING_MODEL = "models/text-embedding-004"
EMBEDDING_DIMS = 768


def _embed_sync(text: str) -> list[float]:
    """Synchronous embedding call — run in executor for async usage."""
    import google.generativeai as genai
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_document",
    )
    return result["embedding"]


async def get_embedding(text: str) -> list[float] | None:
    """Async embedding via Google text-embedding-004 (768 dims).

    Returns None if embedding is disabled or fails.
    """
    if not settings.embedding_enabled or not text.strip():
        return None
    try:
        loop = asyncio.get_running_loop()
        embedding = await loop.run_in_executor(None, partial(_embed_sync, text))
        logger.debug(f"Embedding: {len(embedding)} dims for {len(text)} chars")
        return embedding
    except Exception as exc:
        logger.warning(f"Embedding failed: {exc}")
        return None


async def get_query_embedding(text: str) -> list[float] | None:
    """Embedding for search queries (uses retrieval_query task type)."""
    if not settings.embedding_enabled or not text.strip():
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: genai.embed_content(
                model=EMBEDDING_MODEL,
                content=text,
                task_type="retrieval_query",
            ),
        )
        return result["embedding"]
    except Exception as exc:
        logger.warning(f"Query embedding failed: {exc}")
        return None
