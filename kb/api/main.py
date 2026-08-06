from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routers import kb
from api.schemas import HealthResponse
from config.logger import logger, setup_logging
from config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info(f"KB Service started | embedding={settings.embedding_enabled} | threshold={settings.KB_SIMILARITY_THRESHOLD}")
    await _seed_api_key()
    yield
    logger.info("KB Service stopped")


async def _seed_api_key() -> None:
    """KB_SEED_API_KEY .env da bo'lsa, avtomatik yaratadi."""
    if not settings.KB_SEED_API_KEY:
        return
    from database.connection import get_session
    from database.repositories import ApiKeyRepository
    try:
        async with get_session() as session:
            repo = ApiKeyRepository(session)
            existing = await repo.get_project_id(settings.KB_SEED_API_KEY)
            if existing is None:
                await repo.create(
                    settings.KB_SEED_API_KEY,
                    settings.KB_SEED_PROJECT_ID,
                    "Auto-seeded from env",
                )
                logger.info(f"API key yaratildi: project={settings.KB_SEED_PROJECT_ID}")
            else:
                logger.info(f"API key mavjud: project={existing}")
    except Exception as exc:
        logger.warning(f"API key seed xatolik: {exc}")


app = FastAPI(
    title="Knowledge Base API",
    version="1.0.0",
    description="Shared self-learning error knowledge base with semantic search.",
    lifespan=lifespan,
)

app.include_router(kb.router)


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    return HealthResponse(embedding_enabled=settings.embedding_enabled)
