from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session, sessionmaker

from app.models.graph_outbox import GraphOutboxEvent, GraphOutboxStatus
from app.services.graph_sync import process_graph_outbox_batch


class RecordingFusekiClient:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.updates: list[str] = []

    def update(self, sparql: str) -> None:
        self.updates.append(sparql)
        if self.error is not None:
            raise self.error


def add_card_event(
    test_session_factory: sessionmaker[Session],
    *,
    title: str = "정보처리기사",
) -> int:
    with test_session_factory() as session:
        event = GraphOutboxEvent(
            aggregate_type="card",
            aggregate_id="1",
            event_type="upsert",
            payload={
                "schema_version": 1,
                "entity": {
                    "id": 1,
                    "profile_id": 1,
                    "title": title,
                    "description": None,
                },
            },
        )
        session.add(event)
        session.commit()
        return event.id


def process_batch(
    test_session_factory: sessionmaker[Session],
    client: RecordingFusekiClient,
    *,
    max_attempts: int = 5,
):
    return process_graph_outbox_batch(
        test_session_factory,
        client,
        batch_size=25,
        max_attempts=max_attempts,
        lock_timeout_seconds=60,
    )


def test_graph_sync_completes_successful_event(
    test_session_factory: sessionmaker[Session],
) -> None:
    event_id = add_card_event(test_session_factory)
    client = RecordingFusekiClient()

    result = process_batch(test_session_factory, client)

    assert (result.claimed, result.completed, result.retried, result.failed) == (1, 1, 0, 0)
    assert len(client.updates) == 1
    with test_session_factory() as session:
        event = session.get(GraphOutboxEvent, event_id)
        assert event is not None
        assert event.status == GraphOutboxStatus.COMPLETED.value
        assert event.attempt_count == 1
        assert event.processed_at is not None
        assert event.locked_at is None


def test_graph_sync_retries_failure_without_processing_later_event(
    test_session_factory: sessionmaker[Session],
) -> None:
    first_id = add_card_event(test_session_factory, title="첫 이벤트")
    second_id = add_card_event(test_session_factory, title="둘째 이벤트")
    client = RecordingFusekiClient(RuntimeError("Fuseki unavailable"))

    result = process_batch(test_session_factory, client)

    assert (result.claimed, result.completed, result.retried, result.failed) == (1, 0, 1, 0)
    with test_session_factory() as session:
        first = session.get(GraphOutboxEvent, first_id)
        second = session.get(GraphOutboxEvent, second_id)
        assert first is not None
        assert second is not None
        assert first.status == GraphOutboxStatus.PENDING.value
        assert first.attempt_count == 1
        assert first.last_error == "Fuseki unavailable"
        assert second.status == GraphOutboxStatus.PENDING.value
        assert second.attempt_count == 0

    next_result = process_batch(test_session_factory, RecordingFusekiClient())

    assert next_result.claimed == 0
    with test_session_factory() as session:
        second = session.get(GraphOutboxEvent, second_id)
        assert second is not None
        assert second.attempt_count == 0


def test_graph_sync_marks_event_failed_after_max_attempts(
    test_session_factory: sessionmaker[Session],
) -> None:
    event_id = add_card_event(test_session_factory)
    client = RecordingFusekiClient(RuntimeError("invalid payload"))

    result = process_batch(test_session_factory, client, max_attempts=1)

    assert (result.claimed, result.completed, result.retried, result.failed) == (1, 0, 0, 1)
    with test_session_factory() as session:
        event = session.get(GraphOutboxEvent, event_id)
        assert event is not None
        assert event.status == GraphOutboxStatus.FAILED.value
        assert event.last_error == "invalid payload"


def test_graph_sync_recovers_stale_processing_event(
    test_session_factory: sessionmaker[Session],
) -> None:
    event_id = add_card_event(test_session_factory)
    with test_session_factory() as session:
        event = session.get(GraphOutboxEvent, event_id)
        assert event is not None
        event.status = GraphOutboxStatus.PROCESSING.value
        event.locked_at = datetime.now(UTC) - timedelta(minutes=5)
        session.commit()

    result = process_batch(test_session_factory, RecordingFusekiClient())

    assert result.completed == 1
    with test_session_factory() as session:
        event = session.get(GraphOutboxEvent, event_id)
        assert event is not None
        assert event.status == GraphOutboxStatus.COMPLETED.value
        assert event.attempt_count == 1
