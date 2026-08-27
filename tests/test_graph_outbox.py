import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.models.graph_outbox import (
    GraphOutboxEvent,
    GraphOutboxEventType,
    GraphOutboxStatus,
)


def test_graph_outbox_event_defaults(
    test_session_factory: sessionmaker[Session],
) -> None:
    with test_session_factory() as session:
        event = GraphOutboxEvent(
            aggregate_type="problem",
            aggregate_id="15",
            event_type=GraphOutboxEventType.UPSERT.value,
            payload={"problem_id": 15},
        )
        session.add(event)
        session.commit()

        saved_event = session.scalar(select(GraphOutboxEvent))

        assert saved_event is not None
        assert saved_event.status == GraphOutboxStatus.PENDING.value
        assert saved_event.attempt_count == 0
        assert saved_event.available_at is not None
        assert saved_event.created_at is not None
        assert saved_event.processed_at is None


def test_graph_outbox_rejects_unknown_event_type(
    test_session_factory: sessionmaker[Session],
) -> None:
    with test_session_factory() as session:
        session.add(
            GraphOutboxEvent(
                aggregate_type="problem",
                aggregate_id="15",
                event_type="unknown",
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()
