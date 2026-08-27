from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.orm import Session, aliased, sessionmaker

from app.models.graph_outbox import GraphOutboxEvent, GraphOutboxStatus
from app.services.graph_rdf import build_graph_update


class SparqlUpdateClient(Protocol):
    def update(self, sparql: str) -> None: ...


@dataclass(frozen=True)
class ClaimedGraphEvent:
    id: int
    aggregate_type: str
    aggregate_id: str
    event_type: str
    payload: dict[str, Any]
    attempt_count: int


@dataclass(frozen=True)
class GraphSyncBatchResult:
    claimed: int = 0
    completed: int = 0
    retried: int = 0
    failed: int = 0


def claim_next_graph_event(
    session_factory: sessionmaker[Session],
    *,
    lock_timeout_seconds: int,
) -> ClaimedGraphEvent | None:
    now = datetime.now(UTC)
    stale_before = now - timedelta(seconds=lock_timeout_seconds)
    with session_factory() as db:
        earlier_event = aliased(GraphOutboxEvent)
        event = db.scalar(
            select(GraphOutboxEvent)
            .where(
                or_(
                    and_(
                        GraphOutboxEvent.status == GraphOutboxStatus.PENDING.value,
                        GraphOutboxEvent.available_at <= now,
                    ),
                    and_(
                        GraphOutboxEvent.status == GraphOutboxStatus.PROCESSING.value,
                        or_(
                            GraphOutboxEvent.locked_at.is_(None),
                            GraphOutboxEvent.locked_at <= stale_before,
                        ),
                    ),
                ),
                ~exists(
                    select(earlier_event.id).where(
                        earlier_event.id < GraphOutboxEvent.id,
                        earlier_event.status.in_(
                            (
                                GraphOutboxStatus.PENDING.value,
                                GraphOutboxStatus.PROCESSING.value,
                            )
                        ),
                    )
                ),
            )
            .order_by(GraphOutboxEvent.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if event is None:
            return None

        event.status = GraphOutboxStatus.PROCESSING.value
        event.attempt_count += 1
        event.locked_at = now
        event.last_error = None
        db.commit()
        return ClaimedGraphEvent(
            id=event.id,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            event_type=event.event_type,
            payload=event.payload,
            attempt_count=event.attempt_count,
        )


def complete_graph_event(
    session_factory: sessionmaker[Session],
    event_id: int,
) -> None:
    with session_factory() as db:
        event = db.scalar(
            select(GraphOutboxEvent).where(GraphOutboxEvent.id == event_id).with_for_update()
        )
        if event is None:
            return
        event.status = GraphOutboxStatus.COMPLETED.value
        event.processed_at = datetime.now(UTC)
        event.locked_at = None
        event.last_error = None
        db.commit()


def fail_graph_event(
    session_factory: sessionmaker[Session],
    event: ClaimedGraphEvent,
    error: Exception,
    *,
    max_attempts: int,
) -> bool:
    terminal = event.attempt_count >= max_attempts
    now = datetime.now(UTC)
    retry_delay = min(2**event.attempt_count, 300)
    with session_factory() as db:
        stored_event = db.scalar(
            select(GraphOutboxEvent).where(GraphOutboxEvent.id == event.id).with_for_update()
        )
        if stored_event is None:
            return terminal
        stored_event.status = (
            GraphOutboxStatus.FAILED.value if terminal else GraphOutboxStatus.PENDING.value
        )
        stored_event.available_at = now + timedelta(seconds=retry_delay)
        stored_event.locked_at = None
        stored_event.last_error = str(error)[:4000]
        db.commit()
    return terminal


def process_graph_outbox_batch(
    session_factory: sessionmaker[Session],
    client: SparqlUpdateClient,
    *,
    batch_size: int,
    max_attempts: int,
    lock_timeout_seconds: int,
) -> GraphSyncBatchResult:
    claimed = 0
    completed = 0
    retried = 0
    failed = 0

    for _ in range(batch_size):
        event = claim_next_graph_event(
            session_factory,
            lock_timeout_seconds=lock_timeout_seconds,
        )
        if event is None:
            break
        claimed += 1
        try:
            update = build_graph_update(
                aggregate_type=event.aggregate_type,
                aggregate_id=event.aggregate_id,
                event_type=event.event_type,
                payload=event.payload,
            )
            client.update(update)
        except Exception as error:
            terminal = fail_graph_event(
                session_factory,
                event,
                error,
                max_attempts=max_attempts,
            )
            if terminal:
                failed += 1
                continue
            retried += 1
            break
        complete_graph_event(session_factory, event.id)
        completed += 1

    return GraphSyncBatchResult(
        claimed=claimed,
        completed=completed,
        retried=retried,
        failed=failed,
    )
