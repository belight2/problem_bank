from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.card import Card
    from app.models.topic import Topic


class ProblemType(StrEnum):
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    FILL_BLANK = "fill_blank"


class Problem(Base):
    __tablename__ = "problems"
    __table_args__ = (
        CheckConstraint(
            "problem_type IN "
            "('short_answer', 'essay', 'multiple_choice', 'true_false', 'fill_blank')",
            name="ck_problems_problem_type",
        ),
        ForeignKeyConstraint(
            ["card_id", "topic_id"],
            ["topics.card_id", "topics.id"],
            name="fk_problems_card_id_topic_id_topics",
            ondelete="RESTRICT",
        ),
        Index("ix_problems_card_id_topic_id", "card_id", "topic_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"))
    topic_id: Mapped[int] = mapped_column()
    question: Mapped[str] = mapped_column(Text)
    problem_type: Mapped[str] = mapped_column(
        String(32),
        default=ProblemType.SHORT_ANSWER.value,
        server_default=ProblemType.SHORT_ANSWER.value,
    )
    choices: Mapped[list[str] | None] = mapped_column(JSON)
    answer: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    card: Mapped["Card"] = relationship(back_populates="problems")
    topic: Mapped["Topic"] = relationship(
        back_populates="problems",
        foreign_keys=[topic_id],
    )

    @property
    def topic_name(self) -> str:
        return self.topic.name
