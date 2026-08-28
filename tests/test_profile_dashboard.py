from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.models.card import Card
from app.models.concept import Concept, ProblemConcept
from app.models.problem import Problem
from app.models.topic import Topic


def test_profile_is_created_once_and_can_be_configured(client: TestClient) -> None:
    initial = client.get("/profile")
    assert initial.status_code == 200
    assert initial.json()["id"] == 1
    assert initial.json()["is_configured"] is False

    configured = client.put(
        "/profile",
        json={
            "display_name": "  준혁  ",
            "timezone": "Asia/Seoul",
            "daily_goal": 15,
        },
    )
    assert configured.status_code == 200
    assert configured.json()["display_name"] == "준혁"
    assert configured.json()["daily_goal"] == 15
    assert configured.json()["is_configured"] is True

    assert (
        client.put(
            "/profile",
            json={"display_name": "준혁", "timezone": "Unknown/Zone", "daily_goal": 15},
        ).status_code
        == 422
    )


def test_dashboard_aggregates_the_local_profile_study_data(client: TestClient) -> None:
    client.put(
        "/profile",
        json={"display_name": "준혁", "timezone": "Asia/Seoul", "daily_goal": 10},
    )
    card = client.post("/cards", json={"title": "SQLD"}).json()
    assert card["profile_id"] == 1
    card_id = card["id"]

    topic_id = client.post(
        f"/cards/{card_id}/topics",
        json={"name": "데이터 모델링"},
    ).json()["id"]
    problem_id = client.post(
        f"/cards/{card_id}/problems",
        json={
            "topic_id": topic_id,
            "question": "식별자란?",
            "answer": "엔터티를 구분하는 속성",
        },
    ).json()["id"]

    problem_set = client.post(f"/cards/{card_id}/problems/random?limit=1").json()
    recorded = client.post(
        f"/cards/{card_id}/problems/random/{problem_set['session_id']}/results",
        json={
            "results": [
                {
                    "problem_id": problem_id,
                    "result": "incorrect",
                    "submitted_answer": "모름",
                }
            ]
        },
    )
    assert recorded.status_code == 200

    dashboard = client.get("/dashboard")
    assert dashboard.status_code == 200
    payload = dashboard.json()
    assert payload["profile"]["display_name"] == "준혁"
    assert payload["card_count"] == 1
    assert payload["topic_count"] == 1
    assert payload["problem_count"] == 1
    assert payload["completed_session_count"] == 1
    assert payload["incorrect_count"] == 1
    assert payload["unresolved_wrong_answer_count"] == 1
    assert payload["today_studied_count"] == 1
    assert payload["weak_topics"][0]["topic_name"] == "데이터 모델링"
    assert payload["weak_topics"][0]["accuracy_rate"] == 0
    assert payload["cards"] == [
        {
            "card_id": card_id,
            "card_title": "SQLD",
            "problem_count": 1,
            "note_count": 0,
            "workbook_count": 0,
            "completed_session_count": 1,
            "correct_count": 0,
            "incorrect_count": 1,
            "accuracy_rate": 0,
            "unresolved_wrong_answer_count": 1,
        }
    ]
    assert payload["recent_studies"][0]["card_id"] == card_id
    assert payload["recent_studies"][0]["workbook_id"] is None
    assert payload["recent_studies"][0]["problem_count"] == 1
    assert payload["recent_studies"][0]["incorrect_count"] == 1


def test_dashboard_surfaces_weak_concepts(
    client: TestClient,
    test_session_factory: sessionmaker[Session],
) -> None:
    client.put(
        "/profile",
        json={"display_name": "준혁", "timezone": "Asia/Seoul", "daily_goal": 10},
    )
    # primary로 연결된 문제(정답 1/오답 3)를 가진 개념을 프로필 1에 심는다.
    with test_session_factory() as session:
        card = Card(profile_id=1, title="SQLD")
        session.add(card)
        session.flush()
        topic = Topic(card_id=card.id, name="정규화")
        session.add(topic)
        session.flush()
        concept = Concept(profile_id=1, name="정규화", name_key="정규화")
        session.add(concept)
        session.flush()
        problem = Problem(
            card_id=card.id,
            topic_id=topic.id,
            question="정규화의 목적은?",
            problem_type="short_answer",
            correct_count=1,
            incorrect_count=3,
        )
        session.add(problem)
        session.flush()
        session.add(
            ProblemConcept(problem_id=problem.id, concept_id=concept.id, role="primary")
        )
        session.commit()

    payload = client.get("/dashboard").json()

    assert len(payload["weak_concepts"]) == 1
    weak = payload["weak_concepts"][0]
    assert weak["name"] == "정규화"
    assert weak["graded_count"] == 4
    assert weak["problem_count"] == 1
    # 라플라스 스무딩: (1+1)/(4+2) = 0.333...
    assert abs(weak["mastery_score"] - 1 / 3) < 1e-9
