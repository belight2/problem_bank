from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, CheckConstraint, DateTime, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GraphOutboxEventType(StrEnum):
    UPSERT = "upsert"
    DELETE = "delete"


class GraphAggregateType(StrEnum):
    CARD = "card"
    TOPIC = "topic"
    PROBLEM = "problem"
    NOTE = "note"


class GraphOutboxStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SUPERSEDED = "superseded"


class GraphOutboxEvent(Base):
    __tablename__ = "graph_outbox"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('upsert', 'delete')",
            name="ck_graph_outbox_event_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed', 'superseded')",
            name="ck_graph_outbox_status",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_graph_outbox_attempt_count_nonnegative",
        ),
        Index(
            "ix_graph_outbox_status_available_at_id",
            "status",
            "available_at",
            "id",
        ),
        Index(
            "ix_graph_outbox_aggregate",
            "aggregate_type",
            "aggregate_id",
            "id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    aggregate_type: Mapped[str] = mapped_column(String(50))
    aggregate_id: Mapped[str] = mapped_column(String(100))
    event_type: Mapped[str] = mapped_column(String(20))
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'"),
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=GraphOutboxStatus.PENDING.value,
        server_default=GraphOutboxStatus.PENDING.value,
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
