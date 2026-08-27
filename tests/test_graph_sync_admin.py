from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models.card import Card
from app.models.graph_outbox import GraphOutboxEvent, GraphOutboxStatus


def create_failed_card_event(
    client: TestClient,
    test_session_factory: sessionmaker[Session],
) -> tuple[dict[str, object], int]:
    card = client.post(
        "/cards",
        json={"title": "정보처리기사", "description": "필기 공부"},
    ).json()
    with test_session_factory() as db:
        event = db.scalar(
            select(GraphOutboxEvent).where(
                GraphOutboxEvent.aggregate_type == "card",
                GraphOutboxEvent.aggregate_id == str(card["id"]),
            )
        )
        assert event is not None
        event.status = GraphOutboxStatus.FAILED.value
        event.attempt_count = 5
        event.last_error = "Fuseki unavailable"
        db.commit()
        return card, event.id


def test_graph_sync_status_and_failed_event_list(
    client: TestClient,
    test_session_factory: sessionmaker[Session],
) -> None:
    _card, event_id = create_failed_card_event(client, test_session_factory)

    status_response = client.get("/graph-sync/status")
    failed_response = client.get("/graph-sync/events/failed")

    assert status_response.status_code == 200
    assert status_response.json() == {
        "worker_enabled": False,
        "pending_count": 0,
        "processing_count": 0,
        "completed_count": 0,
        "failed_count": 1,
        "superseded_count": 0,
        "oldest_open_created_at": None,
        "last_completed_at": None,
    }
    assert failed_response.status_code == 200
    assert failed_response.json()[0]["id"] == event_id
    assert failed_response.json()[0]["last_error"] == "Fuseki unavailable"
    assert "payload" not in failed_response.json()[0]


def test_retry_failed_event_uses_current_entity_state(
    client: TestClient,
    test_session_factory: sessionmaker[Session],
) -> None:
    card, failed_event_id = create_failed_card_event(client, test_session_factory)
    with test_session_factory() as db:
        saved_card = db.get(Card, card["id"])
        assert saved_card is not None
        saved_card.title = "정보처리기사 실기"
        db.commit()

    response = client.post(f"/graph-sync/events/{failed_event_id}/retry")

    assert response.status_code == 201
    payload = response.json()
    assert payload["superseded_event_id"] == failed_event_id
    assert payload["retry_event"]["status"] == GraphOutboxStatus.PENDING.value
    assert payload["retry_event"]["event_type"] == "upsert"
    assert payload["retry_event"]["id"] > failed_event_id

    with test_session_factory() as db:
        failed_event = db.get(GraphOutboxEvent, failed_event_id)
        retry_event = db.get(GraphOutboxEvent, payload["retry_event"]["id"])
        assert failed_event is not None
        assert retry_event is not None
        assert failed_event.status == GraphOutboxStatus.SUPERSEDED.value
        assert failed_event.processed_at is not None
        assert failed_event.last_error == "Fuseki unavailable"
        assert retry_event.payload["entity"]["title"] == "정보처리기사 실기"
        assert retry_event.attempt_count == 0

    assert client.get("/graph-sync/events/failed").json() == []
    status_payload = client.get("/graph-sync/status").json()
    assert status_payload["pending_count"] == 1
    assert status_payload["superseded_count"] == 1


def test_retry_failed_event_creates_delete_when_entity_no_longer_exists(
    client: TestClient,
    test_session_factory: sessionmaker[Session],
) -> None:
    card, failed_event_id = create_failed_card_event(client, test_session_factory)
    with test_session_factory() as db:
        saved_card = db.get(Card, card["id"])
        assert saved_card is not None
        db.delete(saved_card)
        db.commit()

    response = client.post(f"/graph-sync/events/{failed_event_id}/retry")

    assert response.status_code == 201
    retry_event_id = response.json()["retry_event"]["id"]
    assert response.json()["retry_event"]["event_type"] == "delete"
    with test_session_factory() as db:
        retry_event = db.get(GraphOutboxEvent, retry_event_id)
        assert retry_event is not None
        assert retry_event.payload["entity"] == {
            "id": card["id"],
            "cascade": True,
        }


def test_only_failed_events_can_be_retried(
    client: TestClient,
    test_session_factory: sessionmaker[Session],
) -> None:
    card = client.post("/cards", json={"title": "SQLD"}).json()
    with test_session_factory() as db:
        event = db.scalar(
            select(GraphOutboxEvent).where(
                GraphOutboxEvent.aggregate_id == str(card["id"])
            )
        )
        assert event is not None
        event_id = event.id

    assert client.post(f"/graph-sync/events/{event_id}/retry").status_code == 409
    assert client.post("/graph-sync/events/999/retry").status_code == 404
