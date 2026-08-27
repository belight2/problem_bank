import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.dependencies import DatabaseSession
from app.api.routes.cards import router as cards_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.notes import router as notes_router
from app.api.routes.problems import router as problems_router
from app.api.routes.profile import router as profile_router
from app.api.routes.random_study_presets import router as random_study_presets_router
from app.api.routes.random_study_settings import router as random_study_settings_router
from app.api.routes.topics import router as topics_router
from app.api.routes.workbooks import router as workbooks_router
from app.api.routes.wrong_answers import router as wrong_answers_router
from app.core.config import get_settings
from app.workers.graph_sync import run_graph_sync_worker


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    stop_event = asyncio.Event()
    worker_task: asyncio.Task[None] | None = None
    if settings.graph_sync_enabled:
        worker_task = asyncio.create_task(run_graph_sync_worker(stop_event, settings))
    try:
        yield
    finally:
        stop_event.set()
        if worker_task is not None:
            await worker_task


app = FastAPI(title=get_settings().app_name, lifespan=lifespan)
app.include_router(profile_router)
app.include_router(dashboard_router)
app.include_router(cards_router)
app.include_router(notes_router)
app.include_router(topics_router)
app.include_router(problems_router)
app.include_router(random_study_presets_router)
app.include_router(random_study_settings_router)
app.include_router(wrong_answers_router)
app.include_router(workbooks_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": get_settings().app_name, "docs": "/docs"}


@app.get("/health")
def health(db: DatabaseSession) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
