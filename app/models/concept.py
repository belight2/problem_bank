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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.card import Card
    from app.models.note import Note
    from app.models.problem import Problem
    from app.models.profile import Profile


class ProblemConceptRole(StrEnum):
    PRIMARY = "primary"
    SUPPORTING = "supporting"


class ConceptRelationType(StrEnum):
    BROADER = "broader"
    PREREQUISITE = "prerequisite"
    RELATED = "related"
    CONTRASTS = "contrasts"
    CONFUSED_WITH = "confused_with"


class Concept(Base):
    __tablename__ = "concepts"
    __table_args__ = (
        UniqueConstraint("profile_id", "name_key", name="uq_concepts_profile_id_name_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120))
    name_key: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    profile: Mapped["Profile"] = relationship(back_populates="concepts")
    card_links: Mapped[list["CardConcept"]] = relationship(
        back_populates="concept",
        cascade="all, delete-orphan",
    )
    problem_links: Mapped[list["ProblemConcept"]] = relationship(
        back_populates="concept",
        cascade="all, delete-orphan",
    )
    note_links: Mapped[list["NoteConcept"]] = relationship(
        back_populates="concept",
        cascade="all, delete-orphan",
    )
    outgoing_relations: Mapped[list["ConceptRelation"]] = relationship(
        back_populates="source_concept",
        foreign_keys="ConceptRelation.source_concept_id",
        cascade="all, delete-orphan",
    )
    incoming_relations: Mapped[list["ConceptRelation"]] = relationship(
        back_populates="target_concept",
        foreign_keys="ConceptRelation.target_concept_id",
        cascade="all, delete-orphan",
    )


class CardConcept(Base):
    __tablename__ = "card_concepts"

    card_id: Mapped[int] = mapped_column(
        ForeignKey("cards.id", ondelete="CASCADE"),
        primary_key=True,
    )
    concept_id: Mapped[int] = mapped_column(
        ForeignKey("concepts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    card: Mapped["Card"] = relationship(back_populates="concept_links")
    concept: Mapped["Concept"] = relationship(back_populates="card_links")


class ProblemConcept(Base):
    __tablename__ = "problem_concepts"
    __table_args__ = (
        CheckConstraint(
            "role IN ('primary', 'supporting')",
            name="ck_problem_concepts_role",
        ),
        Index(
            "uq_problem_concepts_one_primary",
            "problem_id",
            unique=True,
            postgresql_where=text("role = 'primary'"),
            sqlite_where=text("role = 'primary'"),
        ),
    )

    problem_id: Mapped[int] = mapped_column(
        ForeignKey("problems.id", ondelete="CASCADE"),
        primary_key=True,
    )
    concept_id: Mapped[int] = mapped_column(
        ForeignKey("concepts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    problem: Mapped["Problem"] = relationship(back_populates="concept_links")
    concept: Mapped["Concept"] = relationship(back_populates="problem_links")


class NoteConcept(Base):
    __tablename__ = "note_concepts"

    note_id: Mapped[int] = mapped_column(
        ForeignKey("notes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    concept_id: Mapped[int] = mapped_column(
        ForeignKey("concepts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    note: Mapped["Note"] = relationship(back_populates="concept_links")
    concept: Mapped["Concept"] = relationship(back_populates="note_links")


class ConceptRelation(Base):
    __tablename__ = "concept_relations"
    __table_args__ = (
        CheckConstraint(
            "relation_type IN ('broader', 'prerequisite', 'related', 'contrasts', 'confused_with')",
            name="ck_concept_relations_type",
        ),
        CheckConstraint(
            "source_concept_id <> target_concept_id",
            name="ck_concept_relations_distinct_concepts",
        ),
        UniqueConstraint(
            "source_concept_id",
            "target_concept_id",
            "relation_type",
            name="uq_concept_relations_source_target_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_concept_id: Mapped[int] = mapped_column(
        ForeignKey("concepts.id", ondelete="CASCADE"),
        index=True,
    )
    target_concept_id: Mapped[int] = mapped_column(
        ForeignKey("concepts.id", ondelete="CASCADE"),
        index=True,
    )
    relation_type: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source_concept: Mapped["Concept"] = relationship(
        back_populates="outgoing_relations",
        foreign_keys=[source_concept_id],
    )
    target_concept: Mapped["Concept"] = relationship(
        back_populates="incoming_relations",
        foreign_keys=[target_concept_id],
    )

    @property
    def source_concept_name(self) -> str:
        return self.source_concept.name

    @property
    def target_concept_name(self) -> str:
        return self.target_concept.name
