from collections.abc import Sequence

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.models.concept import Concept, ProblemConcept
from app.models.problem import Problem


def _make_card(client: TestClient) -> tuple[int, int]:
    client.put(
        "/profile",
        json={"display_name": "준혁", "timezone": "Asia/Seoul", "daily_goal": 10},
    )
    card = client.post("/cards", json={"title": "정보처리기사"}).json()
    topic = client.post(
        f"/cards/{card['id']}/topics", json={"name": "데이터베이스"}
    ).json()
    return card["id"], topic["id"]


def _add_concept(
    factory: sessionmaker[Session],
    *,
    card_id: int,
    topic_id: int,
    name: str,
    problems: Sequence[tuple[int, int]],
) -> tuple[int, list[int]]:
    """problems: (correct_count, incorrect_count) per primary-linked problem."""
    with factory() as session:
        concept = Concept(profile_id=1, name=name, name_key=name)
        session.add(concept)
        session.flush()
        problem_ids: list[int] = []
        for correct, incorrect in problems:
            problem = Problem(
                card_id=card_id,
                topic_id=topic_id,
                question=f"{name} 문제",
                problem_type="short_answer",
                answer="정답",
                correct_count=correct,
                incorrect_count=incorrect,
            )
            session.add(problem)
            session.flush()
            session.add(
                ProblemConcept(
                    problem_id=problem.id, concept_id=concept.id, role="primary"
                )
            )
            problem_ids.append(problem.id)
        session.commit()
        return concept.id, problem_ids


def test_concept_study_creates_session_gradable_by_existing_endpoint(
    client: TestClient,
    test_session_factory: sessionmaker[Session],
) -> None:
    card_id, topic_id = _make_card(client)
    concept_id, problem_ids = _add_concept(
        test_session_factory,
        card_id=card_id,
        topic_id=topic_id,
        name="트랜잭션",
        problems=[(1, 4), (0, 3)],
    )

    started = client.post(f"/cards/{card_id}/concepts/{concept_id}/study")
    assert started.status_code == 200
    payload = started.json()
    assert payload["session_id"] is not None
    assert {p["id"] for p in payload["problems"]} == set(problem_ids)

    # 핵심 재사용: workbook 없이 만든 임시 세션이 기존 채점 엔드포인트로 그대로 채점된다.
    graded = client.post(
        f"/cards/{card_id}/problems/random/{payload['session_id']}/results",
        json={
            "results": [
                {"problem_id": pid, "result": "incorrect", "submitted_answer": "모름"}
                for pid in problem_ids
            ]
        },
    )
    assert graded.status_code == 200
    assert graded.json()["status"] == "recorded"
    # 채점이 오답노트에 반영됐는지(루프 확인).
    wrong = client.get(f"/cards/{card_id}/wrong-answers").json()
    assert {w["problem_id"] for w in wrong} == set(problem_ids)


def test_concept_study_empty_without_primary_problems(
    client: TestClient,
    test_session_factory: sessionmaker[Session],
) -> None:
    card_id, topic_id = _make_card(client)
    # supporting로만 연결 → primary 문제 0개 → 빈 세션.
    with test_session_factory() as session:
        concept = Concept(profile_id=1, name="락킹", name_key="락킹")
        session.add(concept)
        session.flush()
        problem = Problem(
            card_id=card_id,
            topic_id=topic_id,
            question="q",
            problem_type="short_answer",
            answer="a",
        )
        session.add(problem)
        session.flush()
        session.add(
            ProblemConcept(
                problem_id=problem.id, concept_id=concept.id, role="supporting"
            )
        )
        session.commit()
        concept_id = concept.id

    response = client.post(f"/cards/{card_id}/concepts/{concept_id}/study")
    assert response.status_code == 200
    assert response.json() == {"session_id": None, "problems": []}


def test_concept_study_404_for_unknown_concept(client: TestClient) -> None:
    card_id, _ = _make_card(client)
    assert client.post(f"/cards/{card_id}/concepts/99999/study").status_code == 404


def test_card_weak_concepts_ranked_ascending(
    client: TestClient,
    test_session_factory: sessionmaker[Session],
) -> None:
    card_id, topic_id = _make_card(client)
    _add_concept(
        test_session_factory,
        card_id=card_id,
        topic_id=topic_id,
        name="트랜잭션",
        problems=[(9, 1)],  # 강함 0.83
    )
    weak_id, _ = _add_concept(
        test_session_factory,
        card_id=card_id,
        topic_id=topic_id,
        name="락킹",
        problems=[(0, 8)],  # 약함 0.10
    )

    items = client.get(f"/cards/{card_id}/weak-concepts").json()
    assert len(items) == 2
    # 약한 것이 먼저.
    assert items[0]["concept_id"] == weak_id
    assert items[0]["name"] == "락킹"
    assert items[0]["mastery_score"] < items[1]["mastery_score"]
