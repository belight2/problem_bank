from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.card import Card
    from app.models.concept import Concept


class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = (
        CheckConstraint(
            "daily_goal BETWEEN 1 AND 100",
            name="ck_profiles_daily_goal",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(
        String(80),
        default="사용자",
        server_default="사용자",
    )
    timezone: Mapped[str] = mapped_column(
        String(64),
        default="Asia/Seoul",
        server_default="Asia/Seoul",
    )
    daily_goal: Mapped[int] = mapped_column(default=20, server_default="20")
    is_configured: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
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

    cards: Mapped[list["Card"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
    )
    concepts: Mapped[list["Concept"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
    )
