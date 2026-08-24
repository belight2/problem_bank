from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db

DatabaseSession = Annotated[Session, Depends(get_db)]

app = FastAPI(title=get_settings().app_name)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": get_settings().app_name, "docs": "/docs"}


@app.get("/health")
def health(db: DatabaseSession) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
