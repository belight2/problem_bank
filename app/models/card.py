from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.concept import CardConcept
    from app.models.note import Note
    from app.models.problem import Problem
    from app.models.profile import Profile
    from app.models.random_study_preset import RandomStudyPreset
    from app.models.random_study_setting import RandomStudySetting
    from app.models.topic import Topic
    from app.models.workbook import Workbook
    from app.models.wrong_answer import WrongAnswer


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"),
        default=1,
        server_default="1",
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    profile: Mapped["Profile"] = relationship(back_populates="cards")

    problems: Mapped[list["Problem"]] = relationship(
        back_populates="card", cascade="all, delete-orphan"
    )
    topics: Mapped[list["Topic"]] = relationship(
        back_populates="card", cascade="all, delete-orphan"
    )
    notes: Mapped[list["Note"]] = relationship(back_populates="card", cascade="all, delete-orphan")
    random_study_setting: Mapped["RandomStudySetting | None"] = relationship(
        back_populates="card",
        cascade="all, delete-orphan",
        uselist=False,
    )
    random_study_presets: Mapped[list["RandomStudyPreset"]] = relationship(
        back_populates="card",
        cascade="all, delete-orphan",
    )
    wrong_answers: Mapped[list["WrongAnswer"]] = relationship(
        back_populates="card",
        cascade="all, delete-orphan",
    )
    workbooks: Mapped[list["Workbook"]] = relationship(
        back_populates="card",
        cascade="all, delete-orphan",
    )
    concept_links: Mapped[list["CardConcept"]] = relationship(
        back_populates="card",
        cascade="all, delete-orphan",
    )

    @property
    def concept_ids(self) -> list[int]:
        return [link.concept_id for link in self.concept_links]
