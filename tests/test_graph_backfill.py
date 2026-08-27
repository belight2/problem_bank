from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.graph_outbox import GraphOutboxEvent
from app.services.graph_backfill import enqueue_graph_backfill


def test_graph_backfill_enqueues_existing_entities_in_dependency_order(
    client: TestClient,
    test_session_factory: sessionmaker[Session],
) -> None:
    card = client.post("/cards", json={"title": "정보처리기사"}).json()
    concept = client.post(
        "/concepts",
        json={"name": "정규화"},
    ).json()
    assert client.put(f"/cards/{card['id']}/concepts/{concept['id']}").status_code == 200
    topic = client.post(
        f"/cards/{card['id']}/topics",
        json={"name": "데이터베이스"},
    ).json()
    note = client.post(
        f"/cards/{card['id']}/notes",
        json={
            "title": "정규화 정리",
            "content_markdown": "# 정규화\n\n중복을 줄입니다.",
            "topic_id": topic["id"],
            "concept_ids": [concept["id"]],
        },
    ).json()
    problem = client.post(
        f"/cards/{card['id']}/problems",
        json={
            "topic_id": topic["id"],
            "question": "정규화의 목적은?",
            "answer": "중복 제거",
            "source_note_id": note["id"],
            "primary_concept_id": concept["id"],
        },
    ).json()

    with test_session_factory() as db:
        db.execute(delete(GraphOutboxEvent))
        db.commit()

        result = enqueue_graph_backfill(db)
        db.commit()

        events = list(db.scalars(select(GraphOutboxEvent).order_by(GraphOutboxEvent.id)))

    assert (
        result.concepts,
        result.cards,
        result.topics,
        result.notes,
        result.problems,
        result.total,
    ) == (
        1,
        1,
        1,
        1,
        1,
        5,
    )
    assert [event.aggregate_type for event in events] == [
        "concept",
        "card",
        "topic",
        "note",
        "problem",
    ]
    assert [event.aggregate_id for event in events] == [
        str(concept["id"]),
        str(card["id"]),
        str(topic["id"]),
        str(note["id"]),
        str(problem["id"]),
    ]
    assert all(event.event_type == "upsert" for event in events)
    assert "content_markdown" not in events[3].payload["entity"]
    assert "answer" not in events[4].payload["entity"]
    assert events[1].payload["entity"]["concept_ids"] == [concept["id"]]
    assert events[3].payload["entity"]["concept_ids"] == [concept["id"]]
    assert events[4].payload["entity"]["primary_concept_id"] == concept["id"]


def test_graph_backfill_with_no_entities_creates_no_events(
    test_session_factory: sessionmaker[Session],
) -> None:
    with test_session_factory() as db:
        result = enqueue_graph_backfill(db)
        db.commit()

        events = list(db.scalars(select(GraphOutboxEvent)))

    assert result.total == 0
    assert events == []
