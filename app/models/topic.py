from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.card import Card
    from app.models.note import Note
    from app.models.problem import Problem


class Topic(Base):
    __tablename__ = "topics"
    __table_args__ = (
        UniqueConstraint("card_id", "id", name="uq_topics_card_id_id"),
        UniqueConstraint("card_id", "name", name="uq_topics_card_id_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    card: Mapped["Card"] = relationship(back_populates="topics")
    problems: Mapped[list["Problem"]] = relationship(
        back_populates="topic",
        foreign_keys="Problem.topic_id",
        passive_deletes=True,
    )
    notes: Mapped[list["Note"]] = relationship(
        back_populates="topic",
        passive_deletes=True,
    )
