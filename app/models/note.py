from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.card import Card
    from app.models.concept import NoteConcept
    from app.models.problem import Problem
    from app.models.topic import Topic


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(
        ForeignKey("cards.id", ondelete="CASCADE"),
        index=True,
    )
    topic_id: Mapped[int | None] = mapped_column(
        ForeignKey("topics.id", ondelete="SET NULL"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200))
    content_markdown: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    card: Mapped["Card"] = relationship(back_populates="notes")
    topic: Mapped["Topic | None"] = relationship(back_populates="notes")
    derived_problems: Mapped[list["Problem"]] = relationship(
        back_populates="source_note",
        passive_deletes=True,
    )
    concept_links: Mapped[list["NoteConcept"]] = relationship(
        back_populates="note",
        cascade="all, delete-orphan",
    )

    @property
    def topic_name(self) -> str | None:
        return self.topic.name if self.topic is not None else None

    @property
    def concept_ids(self) -> list[int]:
        return [link.concept_id for link in self.concept_links]
