from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.problem import Problem
    from app.models.random_study_preset import RandomStudyPreset
    from app.models.random_study_setting import RandomStudySetting
    from app.models.topic import Topic


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    problems: Mapped[list["Problem"]] = relationship(
        back_populates="card", cascade="all, delete-orphan"
    )
    topics: Mapped[list["Topic"]] = relationship(
        back_populates="card", cascade="all, delete-orphan"
    )
    random_study_setting: Mapped["RandomStudySetting | None"] = relationship(
        back_populates="card",
        cascade="all, delete-orphan",
        uselist=False,
    )
    random_study_presets: Mapped[list["RandomStudyPreset"]] = relationship(
        back_populates="card",
        cascade="all, delete-orphan",
    )
