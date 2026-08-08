from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import ErrorCreate, ErrorRead, HealthResponse, OCRLogRead
from api.admin import auth as admin_auth
from api.admin import errors as admin_errors
from api.admin import groups as admin_groups
from api.admin import stats as admin_stats
from config.logger import logger, setup_logging
from database.connection import get_session
from database.repositories import ErrorRepository, OCRLogRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("FastAPI ishga tushdi")
    yield
    logger.info("FastAPI to'xtatildi")


app = FastAPI(
    title="Support Bot API",
    version="0.2.0",
    description="Telegram Support Bot uchun REST API + Admin Panel",
    lifespan=lifespan,
)

# CORS — admin panel uchun
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # production da aniq domain ko'rsating
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Admin routers
app.include_router(admin_auth.router)
app.include_router(admin_errors.router)
app.include_router(admin_groups.router)
app.include_router(admin_stats.router)


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    return HealthResponse()


@app.get("/errors", response_model=list[ErrorRead], tags=["errors"])
async def list_errors() -> list[ErrorRead]:
    async with get_session() as session:
        repo = ErrorRepository(session)
        items = await repo.list_all()
        return [ErrorRead.model_validate(i) for i in items]


@app.post(
    "/errors",
    response_model=ErrorRead,
    status_code=status.HTTP_201_CREATED,
    tags=["errors"],
)
async def create_error(payload: ErrorCreate) -> ErrorRead:
    async with get_session() as session:
        repo = ErrorRepository(session)
        entry = await repo.create(
            title=payload.title,
            keywords=payload.keywords,
            solution=payload.solution,
            description=payload.description,
        )
        return ErrorRead.model_validate(entry)


@app.get("/errors/{error_id}", response_model=ErrorRead, tags=["errors"])
async def get_error(error_id: int) -> ErrorRead:
    async with get_session() as session:
        repo = ErrorRepository(session)
        entry = await repo.get_by_id(error_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="Error not found")
        return ErrorRead.model_validate(entry)


@app.delete(
    "/errors/{error_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    tags=["errors"],
)
async def delete_error(error_id: int):
    async with get_session() as session:
        repo = ErrorRepository(session)
        deleted = await repo.delete(error_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Error not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/logs", response_model=list[OCRLogRead], tags=["logs"])
async def list_logs(limit: int = 50) -> list[OCRLogRead]:
    limit = max(1, min(limit, 500))
    async with get_session() as session:
        repo = OCRLogRepository(session)
        items = await repo.list_recent(limit=limit)
        return [OCRLogRead.model_validate(i) for i in items]
