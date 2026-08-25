from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.card import Card
    from app.models.topic import Topic


class RandomStudyPreset(Base):
    __tablename__ = "random_study_presets"
    __table_args__ = (
        UniqueConstraint(
            "card_id",
            "name",
            name="uq_random_study_presets_card_id_name",
        ),
        CheckConstraint(
            "problem_count BETWEEN 1 AND 100",
            name="ck_random_study_presets_problem_count",
        ),
        CheckConstraint(
            "selection_mode IN ('all', 'incorrect_rate', 'incorrect_count')",
            name="ck_random_study_presets_selection_mode",
        ),
        CheckConstraint(
            "incorrect_rate_threshold BETWEEN 1 AND 100",
            name="ck_random_study_presets_incorrect_rate_threshold",
        ),
        CheckConstraint(
            "minimum_attempt_count >= 1",
            name="ck_random_study_presets_minimum_attempt_count",
        ),
        CheckConstraint(
            "incorrect_count_threshold >= 1",
            name="ck_random_study_presets_incorrect_count_threshold",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    topic_id: Mapped[int | None] = mapped_column(
        ForeignKey("topics.id", ondelete="SET NULL"),
        index=True,
    )
    problem_count: Mapped[int]
    selection_mode: Mapped[str] = mapped_column(String(20), default="all", server_default="all")
    incorrect_rate_threshold: Mapped[int] = mapped_column(default=50, server_default="50")
    minimum_attempt_count: Mapped[int] = mapped_column(default=3, server_default="3")
    incorrect_count_threshold: Mapped[int] = mapped_column(default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    card: Mapped["Card"] = relationship(back_populates="random_study_presets")
    topic: Mapped["Topic | None"] = relationship()
