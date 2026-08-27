from typing import Any

from sqlalchemy.orm import Session

from app.models.card import Card
from app.models.concept import Concept
from app.models.graph_outbox import (
    GraphAggregateType,
    GraphOutboxEvent,
    GraphOutboxEventType,
)
from app.models.note import Note
from app.models.problem import Problem
from app.models.topic import Topic

GRAPH_PAYLOAD_SCHEMA_VERSION = 1


def graph_payload(entity: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": GRAPH_PAYLOAD_SCHEMA_VERSION,
        "entity": entity,
    }


def card_graph_entity(card: Card) -> dict[str, Any]:
    return {
        "id": card.id,
        "profile_id": card.profile_id,
        "title": card.title,
        "description": card.description,
        "concept_ids": sorted(card.concept_ids),
    }


def topic_graph_entity(topic: Topic) -> dict[str, Any]:
    return {
        "id": topic.id,
        "card_id": topic.card_id,
        "name": topic.name,
    }


def problem_graph_entity(problem: Problem) -> dict[str, Any]:
    return {
        "id": problem.id,
        "card_id": problem.card_id,
        "topic_id": problem.topic_id,
        "question": problem.question,
        "problem_type": problem.problem_type,
        "source_note_id": problem.source_note_id,
        "presented_count": problem.presented_count,
        "correct_count": problem.correct_count,
        "incorrect_count": problem.incorrect_count,
        "primary_concept_id": problem.primary_concept_id,
        "supporting_concept_ids": sorted(problem.supporting_concept_ids),
    }


def note_graph_entity(note: Note) -> dict[str, Any]:
    return {
        "id": note.id,
        "card_id": note.card_id,
        "topic_id": note.topic_id,
        "title": note.title,
        "concept_ids": sorted(note.concept_ids),
    }


def concept_graph_entity(concept: Concept) -> dict[str, Any]:
    return {
        "id": concept.id,
        "name": concept.name,
        "description": concept.description,
        "relations": [
            {
                "target_concept_id": relation.target_concept_id,
                "relation_type": relation.relation_type,
            }
            for relation in sorted(concept.outgoing_relations, key=lambda item: item.id or 0)
        ],
    }


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
        payload=graph_payload(entity),
    )
    db.add(event)
    return event


def enqueue_card_event(
    db: Session,
    card: Card,
    event_type: GraphOutboxEventType = GraphOutboxEventType.UPSERT,
) -> GraphOutboxEvent:
    entity = card_graph_entity(card)
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
        entity=topic_graph_entity(topic),
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
        entity=problem_graph_entity(problem),
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
        entity=note_graph_entity(note),
    )


def enqueue_concept_event(
    db: Session,
    concept: Concept,
    event_type: GraphOutboxEventType = GraphOutboxEventType.UPSERT,
) -> GraphOutboxEvent:
    return enqueue_graph_event(
        db,
        aggregate_type=GraphAggregateType.CONCEPT,
        aggregate_id=concept.id,
        event_type=event_type,
        entity=concept_graph_entity(concept),
    )
