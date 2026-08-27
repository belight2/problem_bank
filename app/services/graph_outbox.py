from typing import Any

from sqlalchemy.orm import Session

from app.models.card import Card
from app.models.graph_outbox import (
    GraphAggregateType,
    GraphOutboxEvent,
    GraphOutboxEventType,
)
from app.models.note import Note
from app.models.problem import Problem
from app.models.topic import Topic

GRAPH_PAYLOAD_SCHEMA_VERSION = 1


def enqueue_graph_event(
    db: Session,
    *,
    aggregate_type: GraphAggregateType,
    aggregate_id: int,
    event_type: GraphOutboxEventType,
    entity: dict[str, Any],
) -> GraphOutboxEvent:
    event = GraphOutboxEvent(
        aggregate_type=aggregate_type.value,
        aggregate_id=str(aggregate_id),
        event_type=event_type.value,
        payload={
            "schema_version": GRAPH_PAYLOAD_SCHEMA_VERSION,
            "entity": entity,
        },
    )
    db.add(event)
    return event


def enqueue_card_event(
    db: Session,
    card: Card,
    event_type: GraphOutboxEventType = GraphOutboxEventType.UPSERT,
) -> GraphOutboxEvent:
    entity: dict[str, Any] = {
        "id": card.id,
        "profile_id": card.profile_id,
        "title": card.title,
        "description": card.description,
    }
    if event_type is GraphOutboxEventType.DELETE:
        entity["cascade"] = True
    return enqueue_graph_event(
        db,
        aggregate_type=GraphAggregateType.CARD,
        aggregate_id=card.id,
        event_type=event_type,
        entity=entity,
    )


def enqueue_topic_event(
    db: Session,
    topic: Topic,
    event_type: GraphOutboxEventType = GraphOutboxEventType.UPSERT,
) -> GraphOutboxEvent:
    return enqueue_graph_event(
        db,
        aggregate_type=GraphAggregateType.TOPIC,
        aggregate_id=topic.id,
        event_type=event_type,
        entity={
            "id": topic.id,
            "card_id": topic.card_id,
            "name": topic.name,
        },
    )


def enqueue_problem_event(
    db: Session,
    problem: Problem,
    event_type: GraphOutboxEventType = GraphOutboxEventType.UPSERT,
) -> GraphOutboxEvent:
    return enqueue_graph_event(
        db,
        aggregate_type=GraphAggregateType.PROBLEM,
        aggregate_id=problem.id,
        event_type=event_type,
        entity={
            "id": problem.id,
            "card_id": problem.card_id,
            "topic_id": problem.topic_id,
            "question": problem.question,
            "problem_type": problem.problem_type,
            "source_note_id": problem.source_note_id,
            "presented_count": problem.presented_count,
            "correct_count": problem.correct_count,
            "incorrect_count": problem.incorrect_count,
        },
    )


def enqueue_note_event(
    db: Session,
    note: Note,
    event_type: GraphOutboxEventType = GraphOutboxEventType.UPSERT,
) -> GraphOutboxEvent:
    return enqueue_graph_event(
        db,
        aggregate_type=GraphAggregateType.NOTE,
        aggregate_id=note.id,
        event_type=event_type,
        entity={
            "id": note.id,
            "card_id": note.card_id,
            "topic_id": note.topic_id,
            "title": note.title,
        },
    )
