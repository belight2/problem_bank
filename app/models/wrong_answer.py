from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.card import Card
    from app.models.problem import Problem


class WrongAnswerStatus(StrEnum):
    NEEDS_REVIEW = "needs_review"
    REVIEWING = "reviewing"
    RESOLVED = "resolved"


class WrongAnswer(Base):
    __tablename__ = "wrong_answers"
    __table_args__ = (
        CheckConstraint(
            "status IN ('needs_review', 'reviewing', 'resolved')",
            name="ck_wrong_answers_status",
        ),
        UniqueConstraint("problem_id", name="uq_wrong_answers_problem_id"),
        Index("ix_wrong_answers_card_id_status", "card_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(
        ForeignKey("cards.id", ondelete="CASCADE"),
        index=True,
    )
    problem_id: Mapped[int] = mapped_column(
        ForeignKey("problems.id", ondelete="CASCADE"),
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=WrongAnswerStatus.NEEDS_REVIEW.value,
        server_default=WrongAnswerStatus.NEEDS_REVIEW.value,
    )
    last_submitted_answer: Mapped[str | None] = mapped_column(Text)
    memo: Mapped[str | None] = mapped_column(Text)
    last_incorrect_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    card: Mapped["Card"] = relationship(back_populates="wrong_answers")
    problem: Mapped["Problem"] = relationship(back_populates="wrong_answer")
