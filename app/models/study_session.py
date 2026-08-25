from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.card import Card


class StudySession(Base):
    __tablename__ = "study_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    card_id: Mapped[int] = mapped_column(
        ForeignKey("cards.id", ondelete="CASCADE"),
        index=True,
    )
    problem_ids: Mapped[list[int]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    card: Mapped["Card"] = relationship()
