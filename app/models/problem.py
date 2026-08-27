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
    from app.models.concept import ProblemConcept
    from app.models.note import Note
    from app.models.topic import Topic
    from app.models.wrong_answer import WrongAnswer


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
        CheckConstraint(
            "presented_count >= 0 AND correct_count >= 0 AND incorrect_count >= 0",
            name="ck_problems_study_counts_nonnegative",
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
    source_note_id: Mapped[int | None] = mapped_column(
        ForeignKey("notes.id", ondelete="SET NULL"),
        index=True,
    )
    presented_count: Mapped[int] = mapped_column(default=0, server_default="0")
    correct_count: Mapped[int] = mapped_column(default=0, server_default="0")
    incorrect_count: Mapped[int] = mapped_column(default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    card: Mapped["Card"] = relationship(back_populates="problems")
    topic: Mapped["Topic"] = relationship(
        back_populates="problems",
        foreign_keys=[topic_id],
    )
    source_note: Mapped["Note | None"] = relationship(back_populates="derived_problems")
    wrong_answer: Mapped["WrongAnswer | None"] = relationship(
        back_populates="problem",
        cascade="all, delete-orphan",
        uselist=False,
    )
    concept_links: Mapped[list["ProblemConcept"]] = relationship(
        back_populates="problem",
        cascade="all, delete-orphan",
    )

    @property
    def topic_name(self) -> str:
        return self.topic.name

    @property
    def source_note_title(self) -> str | None:
        return self.source_note.title if self.source_note is not None else None

    @property
    def primary_concept_id(self) -> int | None:
        return next(
            (link.concept_id for link in self.concept_links if link.role == "primary"),
            None,
        )

    @property
    def supporting_concept_ids(self) -> list[int]:
        return [link.concept_id for link in self.concept_links if link.role == "supporting"]
