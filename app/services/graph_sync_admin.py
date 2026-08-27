from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.card import Card
from app.models.graph_outbox import (
    GraphAggregateType,
    GraphOutboxEvent,
    GraphOutboxEventType,
    GraphOutboxStatus,
)
from app.models.note import Note
from app.models.problem import Problem
from app.models.topic import Topic
from app.services.graph_outbox import (
    card_graph_entity,
    enqueue_graph_event,
    note_graph_entity,
    problem_graph_entity,
    topic_graph_entity,
)


class GraphEventNotRetryableError(ValueError):
    pass


class InvalidGraphEventError(ValueError):
    pass


@dataclass(frozen=True)
class GraphSyncStatusSnapshot:
    pending_count: int
    processing_count: int
    completed_count: int
    failed_count: int
    superseded_count: int
    oldest_open_created_at: datetime | None
    last_completed_at: datetime | None


@dataclass(frozen=True)
class GraphRetryResult:
    superseded_event_id: int
    retry_event: GraphOutboxEvent


def get_graph_sync_status(db: Session) -> GraphSyncStatusSnapshot:
    count_rows = db.execute(
        select(GraphOutboxEvent.status, func.count(GraphOutboxEvent.id)).group_by(
            GraphOutboxEvent.status
        )
    ).all()
    counts = {str(status): int(count) for status, count in count_rows}
    oldest_open_created_at = db.scalar(
        select(func.min(GraphOutboxEvent.created_at)).where(
            GraphOutboxEvent.status.in_(
                (
                    GraphOutboxStatus.PENDING.value,
                    GraphOutboxStatus.PROCESSING.value,
                )
            )
        )
    )
    last_completed_at = db.scalar(
        select(func.max(GraphOutboxEvent.processed_at)).where(
            GraphOutboxEvent.status == GraphOutboxStatus.COMPLETED.value
        )
    )
    return GraphSyncStatusSnapshot(
        pending_count=counts.get(GraphOutboxStatus.PENDING.value, 0),
        processing_count=counts.get(GraphOutboxStatus.PROCESSING.value, 0),
        completed_count=counts.get(GraphOutboxStatus.COMPLETED.value, 0),
        failed_count=counts.get(GraphOutboxStatus.FAILED.value, 0),
        superseded_count=counts.get(GraphOutboxStatus.SUPERSEDED.value, 0),
        oldest_open_created_at=oldest_open_created_at,
        last_completed_at=last_completed_at,
    )


def list_failed_graph_events(
    db: Session,
    *,
    limit: int,
) -> list[GraphOutboxEvent]:
    return list(
        db.scalars(
            select(GraphOutboxEvent)
            .where(GraphOutboxEvent.status == GraphOutboxStatus.FAILED.value)
            .order_by(GraphOutboxEvent.id.desc())
            .limit(limit)
        )
    )


def current_graph_entity(
    db: Session,
    aggregate_type: GraphAggregateType,
    aggregate_id: int,
) -> dict[str, object] | None:
    if aggregate_type is GraphAggregateType.CARD:
        card = db.get(Card, aggregate_id)
        return card_graph_entity(card) if card is not None else None
    if aggregate_type is GraphAggregateType.TOPIC:
        topic = db.get(Topic, aggregate_id)
        return topic_graph_entity(topic) if topic is not None else None
    if aggregate_type is GraphAggregateType.NOTE:
        note = db.get(Note, aggregate_id)
        return note_graph_entity(note) if note is not None else None
    if aggregate_type is GraphAggregateType.PROBLEM:
        problem = db.get(Problem, aggregate_id)
        return problem_graph_entity(problem) if problem is not None else None
    raise InvalidGraphEventError(
        f"지원하지 않는 그래프 엔티티 유형입니다: {aggregate_type}"
    )


def retry_failed_graph_event(db: Session, event_id: int) -> GraphRetryResult | None:
    failed_event = db.scalar(
        select(GraphOutboxEvent)
        .where(GraphOutboxEvent.id == event_id)
        .with_for_update()
    )
    if failed_event is None:
        return None
    if failed_event.status != GraphOutboxStatus.FAILED.value:
        raise GraphEventNotRetryableError("실패 상태인 이벤트만 재처리할 수 있습니다.")

    try:
        aggregate_type = GraphAggregateType(failed_event.aggregate_type)
        aggregate_id = int(failed_event.aggregate_id)
    except ValueError as error:
        raise InvalidGraphEventError("이벤트의 엔티티 유형 또는 ID가 올바르지 않습니다.") from error
    if aggregate_id <= 0:
        raise InvalidGraphEventError("이벤트의 엔티티 ID는 양수여야 합니다.")

    entity = current_graph_entity(db, aggregate_type, aggregate_id)
    event_type = GraphOutboxEventType.UPSERT
    if entity is None:
        event_type = GraphOutboxEventType.DELETE
        entity = {"id": aggregate_id}
        if aggregate_type is GraphAggregateType.CARD:
            entity["cascade"] = True

    retry_event = enqueue_graph_event(
        db,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        event_type=event_type,
        entity=entity,
    )
    db.flush()

    failed_event.status = GraphOutboxStatus.SUPERSEDED.value
    failed_event.processed_at = datetime.now(UTC)
    failed_event.locked_at = None
    return GraphRetryResult(
        superseded_event_id=failed_event.id,
        retry_event=retry_event,
    )
