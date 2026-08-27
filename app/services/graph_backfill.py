from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.card import Card
from app.models.concept import Concept
from app.models.note import Note
from app.models.problem import Problem
from app.models.topic import Topic
from app.services.graph_outbox import (
    enqueue_card_event,
    enqueue_concept_event,
    enqueue_note_event,
    enqueue_problem_event,
    enqueue_topic_event,
)


@dataclass(frozen=True)
class GraphBackfillResult:
    concepts: int
    cards: int
    topics: int
    notes: int
    problems: int

    @property
    def total(self) -> int:
        return self.concepts + self.cards + self.topics + self.notes + self.problems


def lock_graph_source_tables(db: Session) -> None:
    if db.get_bind().dialect.name != "postgresql":
        return
    db.execute(
        text(
            "LOCK TABLE concepts, concept_relations, card_concepts, problem_concepts, "
            "note_concepts, cards, topics, notes, problems, graph_outbox "
            "IN SHARE ROW EXCLUSIVE MODE"
        )
    )


def enqueue_graph_backfill(db: Session) -> GraphBackfillResult:
    lock_graph_source_tables(db)

    concepts = list(db.scalars(select(Concept).order_by(Concept.id)))
    cards = list(db.scalars(select(Card).order_by(Card.id)))
    topics = list(db.scalars(select(Topic).order_by(Topic.id)))
    notes = list(db.scalars(select(Note).order_by(Note.id)))
    problems = list(db.scalars(select(Problem).order_by(Problem.id)))

    for concept in concepts:
        enqueue_concept_event(db, concept)
    for card in cards:
        enqueue_card_event(db, card)
    for topic in topics:
        enqueue_topic_event(db, topic)
    for note in notes:
        enqueue_note_event(db, note)
    for problem in problems:
        enqueue_problem_event(db, problem)

    return GraphBackfillResult(
        concepts=len(concepts),
        cards=len(cards),
        topics=len(topics),
        notes=len(notes),
        problems=len(problems),
    )
