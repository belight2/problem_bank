from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models.graph_outbox import GraphOutboxEvent


def graph_events(
    test_session_factory: sessionmaker[Session],
    aggregate_type: str,
    aggregate_id: int,
) -> list[GraphOutboxEvent]:
    with test_session_factory() as session:
        return list(
            session.scalars(
                select(GraphOutboxEvent)
                .where(
                    GraphOutboxEvent.aggregate_type == aggregate_type,
                    GraphOutboxEvent.aggregate_id == str(aggregate_id),
                )
                .order_by(GraphOutboxEvent.id)
            ).all()
        )


def test_crud_records_graph_events_without_sensitive_content(
    client: TestClient,
    test_session_factory: sessionmaker[Session],
) -> None:
    card = client.post(
        "/cards",
        json={"title": "정보처리기사", "description": "자격증 공부"},
    ).json()
    topic = client.post(
        f"/cards/{card['id']}/topics",
        json={"name": "데이터베이스"},
    ).json()
    note = client.post(
        f"/cards/{card['id']}/notes",
        json={
            "title": "정규화 정리",
            "content_markdown": "# 정규화\n\n중복을 줄이는 과정",
            "topic_id": topic["id"],
        },
    ).json()
    problem = client.post(
        f"/cards/{card['id']}/problems",
        json={
            "topic_id": topic["id"],
            "question": "정규화의 목적은?",
            "answer": "중복 제거",
            "source_note_id": note["id"],
        },
    ).json()

    client.patch(f"/cards/{card['id']}", json={"title": "정보처리기사 필기"})
    client.patch(
        f"/cards/{card['id']}/topics/{topic['id']}",
        json={"name": "관계형 데이터베이스"},
    )
    client.patch(
        f"/cards/{card['id']}/notes/{note['id']}",
        json={"title": "정규화와 이상 현상", "topic_id": None},
    )
    client.patch(
        f"/cards/{card['id']}/problems/{problem['id']}",
        json={
            "question": "정규화를 수행하는 이유는?",
            "source_note_id": None,
        },
    )

    assert client.delete(f"/cards/{card['id']}/problems/{problem['id']}").status_code == 204
    assert client.delete(f"/cards/{card['id']}/notes/{note['id']}").status_code == 204
    assert client.delete(f"/cards/{card['id']}/topics/{topic['id']}").status_code == 204
    assert client.delete(f"/cards/{card['id']}").status_code == 204

    card_events = graph_events(test_session_factory, "card", card["id"])
    topic_events = graph_events(test_session_factory, "topic", topic["id"])
    note_events = graph_events(test_session_factory, "note", note["id"])
    problem_events = graph_events(test_session_factory, "problem", problem["id"])

    assert [event.event_type for event in card_events] == ["upsert", "upsert", "delete"]
    assert [event.event_type for event in topic_events] == ["upsert", "upsert", "delete"]
    assert [event.event_type for event in note_events] == ["upsert", "upsert", "delete"]
    assert [event.event_type for event in problem_events] == ["upsert", "upsert", "delete"]
    assert card_events[-1].payload["entity"]["cascade"] is True
    assert problem_events[0].payload["entity"]["source_note_id"] == note["id"]
    assert problem_events[1].payload["entity"]["source_note_id"] is None
    assert note_events[1].payload["entity"]["topic_id"] is None
    assert "answer" not in problem_events[0].payload["entity"]
    assert "choices" not in problem_events[0].payload["entity"]
    assert "content_markdown" not in note_events[0].payload["entity"]


def test_failed_topic_change_does_not_leave_graph_event(
    client: TestClient,
    test_session_factory: sessionmaker[Session],
) -> None:
    card_id = client.post("/cards", json={"title": "정보처리기사"}).json()["id"]
    topic = client.post(
        f"/cards/{card_id}/topics",
        json={"name": "데이터베이스"},
    ).json()

    duplicate = client.post(
        f"/cards/{card_id}/topics",
        json={"name": "데이터베이스"},
    )

    assert duplicate.status_code == 409
    assert len(graph_events(test_session_factory, "topic", topic["id"])) == 1


def test_problem_statistics_record_graph_events_once_per_change(
    client: TestClient,
    test_session_factory: sessionmaker[Session],
) -> None:
    card_id = client.post("/cards", json={"title": "정보처리기사"}).json()["id"]
    topic_id = client.post(
        f"/cards/{card_id}/topics",
        json={"name": "데이터베이스"},
    ).json()["id"]
    problem = client.post(
        f"/cards/{card_id}/problems",
        json={"topic_id": topic_id, "question": "정규화란?"},
    ).json()

    study_set = client.post(
        f"/cards/{card_id}/problems/random",
        params={"limit": 1},
    ).json()
    results_url = f"/cards/{card_id}/problems/random/{study_set['session_id']}/results"
    result_payload = {"results": [{"problem_id": problem["id"], "result": "correct"}]}
    assert client.post(results_url, json=result_payload).json()["status"] == "recorded"
    assert client.post(results_url, json=result_payload).json()["status"] == "already_recorded"

    events = graph_events(test_session_factory, "problem", problem["id"])

    assert len(events) == 3
    assert events[0].payload["entity"]["presented_count"] == 0
    assert events[1].payload["entity"]["presented_count"] == 1
    assert events[2].payload["entity"]["correct_count"] == 1


def test_starting_workbook_attempt_records_presented_count_event(
    client: TestClient,
    test_session_factory: sessionmaker[Session],
) -> None:
    card_id = client.post("/cards", json={"title": "정보처리기사"}).json()["id"]
    topic_id = client.post(
        f"/cards/{card_id}/topics",
        json={"name": "데이터베이스"},
    ).json()["id"]
    problem = client.post(
        f"/cards/{card_id}/problems",
        json={"topic_id": topic_id, "question": "정규화란?"},
    ).json()

    workbook_response = client.post(
        f"/cards/{card_id}/workbooks",
        json={"problem_count": 1},
    )

    assert workbook_response.status_code == 201
    events = graph_events(test_session_factory, "problem", problem["id"])
    assert len(events) == 2
    assert events[-1].payload["entity"]["presented_count"] == 1
