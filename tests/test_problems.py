from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.problem import Problem


def create_card(client: TestClient, title: str = "정보처리기사") -> int:
    response = client.post("/cards", json={"title": title})
    assert response.status_code == 201
    return response.json()["id"]


def create_problem(
    client: TestClient,
    card_id: int,
    topic: str,
    question: str,
    answer: str | None = None,
) -> dict:
    response = client.post(
        f"/cards/{card_id}/problems",
        json={"topic": topic, "question": question, "answer": answer},
    )
    assert response.status_code == 201
    return response.json()


def test_problem_crud_topic_filter_and_random(client: TestClient) -> None:
    card_id = create_card(client)
    database_problem = create_problem(
        client,
        card_id,
        "데이터베이스",
        "정규화의 목적은 무엇인가?",
        "데이터 중복과 이상 현상을 줄이는 것",
    )
    network_problem = create_problem(
        client,
        card_id,
        "네트워크",
        "TCP의 특징은 무엇인가?",
    )
    second_database_problem = create_problem(
        client,
        card_id,
        "데이터베이스",
        "트랜잭션의 ACID를 설명하시오.",
    )

    list_response = client.get(f"/cards/{card_id}/problems")
    assert list_response.status_code == 200
    assert {problem["id"] for problem in list_response.json()} == {
        database_problem["id"],
        network_problem["id"],
        second_database_problem["id"],
    }

    topic_response = client.get(
        f"/cards/{card_id}/problems",
        params={"topic": "데이터베이스"},
    )
    assert topic_response.status_code == 200
    assert {problem["topic"] for problem in topic_response.json()} == {"데이터베이스"}
    assert len(topic_response.json()) == 2

    random_response = client.get(
        f"/cards/{card_id}/problems/random",
        params={"limit": 2},
    )
    assert random_response.status_code == 200
    random_problems = random_response.json()
    random_problem_ids = [problem["id"] for problem in random_problems]
    assert len(random_problem_ids) == 2
    assert len(set(random_problem_ids)) == 2
    assert {problem["card_id"] for problem in random_problems} == {card_id}

    random_topic_response = client.get(
        f"/cards/{card_id}/problems/random",
        params={"topic": "네트워크", "limit": 10},
    )
    assert random_topic_response.status_code == 200
    assert [problem["id"] for problem in random_topic_response.json()] == [network_problem["id"]]

    update_response = client.patch(
        f"/cards/{card_id}/problems/{network_problem['id']}",
        json={"topic": "통신", "answer": "연결 지향형 프로토콜"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["topic"] == "통신"
    assert update_response.json()["answer"] == "연결 지향형 프로토콜"

    get_response = client.get(f"/cards/{card_id}/problems/{network_problem['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["question"] == "TCP의 특징은 무엇인가?"

    delete_response = client.delete(f"/cards/{card_id}/problems/{network_problem['id']}")
    assert delete_response.status_code == 204
    assert client.get(f"/cards/{card_id}/problems/{network_problem['id']}").status_code == 404


def test_problem_is_scoped_to_its_card(client: TestClient) -> None:
    first_card_id = create_card(client, "정보처리기사")
    second_card_id = create_card(client, "SQLD")
    problem = create_problem(client, first_card_id, "데이터베이스", "기본키란?")

    assert client.get(f"/cards/{second_card_id}/problems/{problem['id']}").status_code == 404
    assert (
        client.patch(
            f"/cards/{second_card_id}/problems/{problem['id']}",
            json={"question": "수정 시도"},
        ).status_code
        == 404
    )
    assert client.delete(f"/cards/{second_card_id}/problems/{problem['id']}").status_code == 404


def test_card_delete_cascades_to_problems(
    client: TestClient,
    test_session_factory: sessionmaker[Session],
) -> None:
    card_id = create_card(client)
    problem = create_problem(client, card_id, "소프트웨어 설계", "UML이란?")

    assert client.delete(f"/cards/{card_id}").status_code == 204

    with test_session_factory() as session:
        count = session.scalar(
            select(func.count()).select_from(Problem).where(Problem.id == problem["id"])
        )
    assert count == 0


def test_problem_list_and_random_for_missing_or_empty_card(client: TestClient) -> None:
    assert client.get("/cards/999/problems").status_code == 404
    assert client.get("/cards/999/problems/random").status_code == 404

    card_id = create_card(client)
    response = client.get(f"/cards/{card_id}/problems/random")
    assert response.status_code == 200
    assert response.json() == []
