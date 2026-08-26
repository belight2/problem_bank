from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.card import Card
    from app.models.workbook import Workbook


class StudySession(Base):
    __tablename__ = "study_sessions"
    __table_args__ = (
        UniqueConstraint(
            "workbook_id",
            "attempt_number",
            name="uq_study_sessions_workbook_id_attempt_number",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    card_id: Mapped[int] = mapped_column(
        ForeignKey("cards.id", ondelete="CASCADE"),
        index=True,
    )
    problem_ids: Mapped[list[int]] = mapped_column(JSON)
    workbook_id: Mapped[int | None] = mapped_column(
        ForeignKey("workbooks.id", ondelete="CASCADE"),
        index=True,
    )
    attempt_number: Mapped[int] = mapped_column(default=1, server_default="1")
    results: Mapped[list[dict[str, object]] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    card: Mapped["Card"] = relationship()
    workbook: Mapped["Workbook | None"] = relationship(back_populates="attempts")

    def result_count(self, result: str) -> int:
        return sum(item.get("result") == result for item in self.results or [])
