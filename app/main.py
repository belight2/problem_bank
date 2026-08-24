from fastapi import FastAPI
from sqlalchemy import text

from app.api.dependencies import DatabaseSession
from app.api.routes.cards import router as cards_router
from app.api.routes.problems import router as problems_router
from app.core.config import get_settings

app = FastAPI(title=get_settings().app_name)
app.include_router(cards_router)
app.include_router(problems_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": get_settings().app_name, "docs": "/docs"}


@app.get("/health")
def health(db: DatabaseSession) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
