import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes.problems import calculate_problem_weight
from app.models.problem import Problem
from app.models.topic import Topic


def create_card(client: TestClient, title: str = "정보처리기사") -> int:
    response = client.post("/cards", json={"title": title})
    assert response.status_code == 201
    return response.json()["id"]


def create_topic(client: TestClient, card_id: int, name: str) -> dict:
    response = client.post(f"/cards/{card_id}/topics", json={"name": name})
    assert response.status_code == 201
    return response.json()


def create_problem(
    client: TestClient,
    card_id: int,
    topic_id: int,
    question: str,
    answer: str | None = None,
    problem_type: str | None = None,
    choices: list[str] | None = None,
) -> dict:
    payload: dict[str, object] = {
        "topic_id": topic_id,
        "question": question,
        "answer": answer,
    }
    if problem_type is not None:
        payload["problem_type"] = problem_type
    if choices is not None:
        payload["choices"] = choices
    response = client.post(
        f"/cards/{card_id}/problems",
        json=payload,
    )
    assert response.status_code == 201
    return response.json()


def test_problem_crud_topic_filter_and_random(client: TestClient) -> None:
    card_id = create_card(client)
    database_topic = create_topic(client, card_id, "데이터베이스")
    network_topic = create_topic(client, card_id, "네트워크")
    database_problem = create_problem(
        client,
        card_id,
        database_topic["id"],
        "정규화의 목적은 무엇인가?",
        "데이터 중복과 이상 현상을 줄이는 것",
    )
    network_problem = create_problem(
        client,
        card_id,
        network_topic["id"],
        "TCP의 특징은 무엇인가?",
    )
    second_database_problem = create_problem(
        client,
        card_id,
        database_topic["id"],
        "트랜잭션의 ACID를 설명하시오.",
    )
    assert database_problem["problem_type"] == "short_answer"
    assert database_problem["choices"] is None
    assert database_problem["topic_id"] == database_topic["id"]
    assert database_problem["topic_name"] == "데이터베이스"

    list_response = client.get(f"/cards/{card_id}/problems")
    assert list_response.status_code == 200
    assert {problem["id"] for problem in list_response.json()} == {
        database_problem["id"],
        network_problem["id"],
        second_database_problem["id"],
    }

    topic_response = client.get(
        f"/cards/{card_id}/problems",
        params={"topic_id": database_topic["id"]},
    )
    assert topic_response.status_code == 200
    assert {problem["topic_id"] for problem in topic_response.json()} == {database_topic["id"]}
    assert len(topic_response.json()) == 2

    random_response = client.post(
        f"/cards/{card_id}/problems/random",
        params={"limit": 2},
    )
    assert random_response.status_code == 200
    random_payload = random_response.json()
    assert random_payload["session_id"] is not None
    random_problems = random_payload["problems"]
    random_problem_ids = [problem["id"] for problem in random_problems]
    assert len(random_problem_ids) == 2
    assert len(set(random_problem_ids)) == 2
    assert {problem["card_id"] for problem in random_problems} == {card_id}

    random_topic_response = client.post(
        f"/cards/{card_id}/problems/random",
        params={"topic_id": network_topic["id"], "limit": 10},
    )
    assert random_topic_response.status_code == 200
    assert [problem["id"] for problem in random_topic_response.json()["problems"]] == [
        network_problem["id"]
    ]

    communication_topic = create_topic(client, card_id, "통신")
    update_response = client.patch(
        f"/cards/{card_id}/problems/{network_problem['id']}",
        json={
            "topic_id": communication_topic["id"],
            "answer": "연결 지향형 프로토콜",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["topic_id"] == communication_topic["id"]
    assert update_response.json()["topic_name"] == "통신"
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
    topic = create_topic(client, first_card_id, "데이터베이스")
    problem = create_problem(client, first_card_id, topic["id"], "기본키란?")

    assert client.get(f"/cards/{second_card_id}/problems/{problem['id']}").status_code == 404
    assert (
        client.patch(
            f"/cards/{second_card_id}/problems/{problem['id']}",
            json={"question": "수정 시도"},
        ).status_code
        == 404
    )
    assert client.delete(f"/cards/{second_card_id}/problems/{problem['id']}").status_code == 404


def test_problem_topic_must_belong_to_same_card(client: TestClient) -> None:
    first_card_id = create_card(client, "정보처리기사")
    second_card_id = create_card(client, "SQLD")
    first_topic = create_topic(client, first_card_id, "데이터베이스")
    second_topic = create_topic(client, second_card_id, "SQL")

    cross_card_create = client.post(
        f"/cards/{first_card_id}/problems",
        json={"topic_id": second_topic["id"], "question": "잘못된 주제인가?"},
    )
    assert cross_card_create.status_code == 404
    assert cross_card_create.json()["detail"] == "Topic not found"

    problem = create_problem(client, first_card_id, first_topic["id"], "기본키란?")
    problem_url = f"/cards/{first_card_id}/problems/{problem['id']}"
    cross_card_update = client.patch(problem_url, json={"topic_id": second_topic["id"]})
    assert cross_card_update.status_code == 404
    assert cross_card_update.json()["detail"] == "Topic not found"
    assert client.get(problem_url).json()["topic_id"] == first_topic["id"]


def test_database_rejects_topic_from_another_card(
    client: TestClient,
    test_session_factory: sessionmaker[Session],
) -> None:
    first_card_id = create_card(client, "정보처리기사")
    second_card_id = create_card(client, "SQLD")
    second_topic = create_topic(client, second_card_id, "SQL")

    with test_session_factory() as session:
        session.add(
            Problem(
                card_id=first_card_id,
                topic_id=second_topic["id"],
                question="다른 카드의 주제를 연결할 수 있는가?",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_card_delete_cascades_to_problems(
    client: TestClient,
    test_session_factory: sessionmaker[Session],
) -> None:
    card_id = create_card(client)
    topic = create_topic(client, card_id, "소프트웨어 설계")
    problem = create_problem(client, card_id, topic["id"], "UML이란?")

    assert client.delete(f"/cards/{card_id}").status_code == 204

    with test_session_factory() as session:
        problem_count = session.scalar(
            select(func.count()).select_from(Problem).where(Problem.id == problem["id"])
        )
        topic_count = session.scalar(
            select(func.count()).select_from(Topic).where(Topic.id == topic["id"])
        )
    assert problem_count == 0
    assert topic_count == 0


def test_problem_list_and_random_for_missing_or_empty_card(client: TestClient) -> None:
    assert client.get("/cards/999/problems").status_code == 404
    assert client.post("/cards/999/problems/random").status_code == 404

    card_id = create_card(client)
    response = client.post(f"/cards/{card_id}/problems/random")
    assert response.status_code == 200
    assert response.json() == {"session_id": None, "problems": []}


def test_study_statistics_are_recorded_once_per_session(client: TestClient) -> None:
    card_id = create_card(client)
    topic = create_topic(client, card_id, "데이터베이스")
    first_problem = create_problem(
        client,
        card_id,
        topic["id"],
        "정규화란?",
    )
    second_problem = create_problem(
        client,
        card_id,
        topic["id"],
        "트랜잭션이란?",
    )

    study_set = client.post(
        f"/cards/{card_id}/problems/random",
        params={"limit": 2},
    )
    assert study_set.status_code == 200
    study_payload = study_set.json()
    assert study_payload["session_id"] is not None
    assert {problem["presented_count"] for problem in study_payload["problems"]} == {1}

    results = [
        {"problem_id": first_problem["id"], "result": "correct"},
        {"problem_id": second_problem["id"], "result": "incorrect"},
    ]
    record_url = (
        f"/cards/{card_id}/problems/random/{study_payload['session_id']}/results"
    )
    recorded = client.post(record_url, json={"results": results})
    assert recorded.status_code == 200
    assert recorded.json()["status"] == "recorded"
    assert len(recorded.json()["problems"]) == 2

    first_saved = client.get(
        f"/cards/{card_id}/problems/{first_problem['id']}"
    ).json()
    second_saved = client.get(
        f"/cards/{card_id}/problems/{second_problem['id']}"
    ).json()
    assert (first_saved["presented_count"], first_saved["correct_count"]) == (1, 1)
    assert first_saved["incorrect_count"] == 0
    assert (second_saved["presented_count"], second_saved["incorrect_count"]) == (1, 1)
    assert second_saved["correct_count"] == 0

    repeated = client.post(record_url, json={"results": results})
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "already_recorded"
    assert len(repeated.json()["problems"]) == 2
    assert client.get(
        f"/cards/{card_id}/problems/{first_problem['id']}"
    ).json()["correct_count"] == 1


def test_study_results_must_match_session_problem_set(client: TestClient) -> None:
    card_id = create_card(client)
    topic = create_topic(client, card_id, "데이터베이스")
    problem = create_problem(client, card_id, topic["id"], "기본키란?")
    study_payload = client.post(
        f"/cards/{card_id}/problems/random",
        params={"limit": 1},
    ).json()

    response = client.post(
        f"/cards/{card_id}/problems/random/{study_payload['session_id']}/results",
        json={"results": [{"problem_id": problem["id"] + 100, "result": "correct"}]},
    )
    assert response.status_code == 422
    saved = client.get(f"/cards/{card_id}/problems/{problem['id']}").json()
    assert saved["correct_count"] == 0
    assert saved["incorrect_count"] == 0


def test_problem_weight_prioritizes_weak_and_underexposed_problems() -> None:
    unseen = Problem(presented_count=0, correct_count=0, incorrect_count=0)
    weak = Problem(presented_count=10, correct_count=1, incorrect_count=9)
    mastered = Problem(presented_count=10, correct_count=9, incorrect_count=1)

    assert calculate_problem_weight(weak) > calculate_problem_weight(unseen)
    assert calculate_problem_weight(unseen) > calculate_problem_weight(mastered)


def test_random_problem_filters_support_incorrect_rate_and_count(
    client: TestClient,
    test_session_factory: sessionmaker[Session],
) -> None:
    card_id = create_card(client)
    topic = create_topic(client, card_id, "데이터베이스")
    rate_match = create_problem(client, card_id, topic["id"], "오답률 조건 일치")
    low_rate = create_problem(client, card_id, topic["id"], "낮은 오답률")
    too_few_attempts = create_problem(client, card_id, topic["id"], "풀이 횟수 부족")
    count_match = create_problem(client, card_id, topic["id"], "오답 횟수 조건 일치")

    statistics = {
        rate_match["id"]: (1, 2),
        low_rate["id"]: (3, 1),
        too_few_attempts["id"]: (0, 1),
        count_match["id"]: (8, 3),
    }
    with test_session_factory() as session:
        for problem_id, (correct_count, incorrect_count) in statistics.items():
            problem = session.get(Problem, problem_id)
            assert problem is not None
            problem.correct_count = correct_count
            problem.incorrect_count = incorrect_count
        session.commit()

    rate_response = client.post(
        f"/cards/{card_id}/problems/random",
        params={
            "limit": 10,
            "selection_mode": "incorrect_rate",
            "incorrect_rate_threshold": 50,
            "minimum_attempt_count": 3,
        },
    )
    assert rate_response.status_code == 200
    assert [problem["id"] for problem in rate_response.json()["problems"]] == [rate_match["id"]]

    count_response = client.post(
        f"/cards/{card_id}/problems/random",
        params={
            "limit": 10,
            "selection_mode": "incorrect_count",
            "incorrect_count_threshold": 2,
        },
    )
    assert count_response.status_code == 200
    assert {problem["id"] for problem in count_response.json()["problems"]} == {
        rate_match["id"],
        count_match["id"],
    }

    no_match_response = client.post(
        f"/cards/{card_id}/problems/random",
        params={
            "selection_mode": "incorrect_rate",
            "incorrect_rate_threshold": 100,
            "minimum_attempt_count": 3,
        },
    )
    assert no_match_response.status_code == 200
    assert no_match_response.json() == {"session_id": None, "problems": []}

    invalid_response = client.post(
        f"/cards/{card_id}/problems/random",
        params={"selection_mode": "incorrect_rate", "incorrect_rate_threshold": 101},
    )
    assert invalid_response.status_code == 422


def test_problem_types_and_choice_normalization(client: TestClient) -> None:
    card_id = create_card(client)
    topic = create_topic(client, card_id, "유형 테스트")

    essay = create_problem(
        client,
        card_id,
        topic["id"],
        "좋은 설계란 무엇인가?",
        problem_type="essay",
    )
    assert essay["problem_type"] == "essay"
    assert essay["choices"] is None

    multiple_choice = create_problem(
        client,
        card_id,
        topic["id"],
        "관계형 데이터베이스의 키는?",
        answer=" 기본키 ",
        problem_type="multiple_choice",
        choices=[" 기본키 ", " 외래키"],
    )
    assert multiple_choice["problem_type"] == "multiple_choice"
    assert multiple_choice["choices"] == ["기본키", "외래키"]
    assert multiple_choice["answer"] == "기본키"

    true_false = create_problem(
        client,
        card_id,
        topic["id"],
        "TCP는 연결 지향형이다.",
        answer=" O ",
        problem_type="true_false",
    )
    assert true_false["problem_type"] == "true_false"
    assert true_false["choices"] is None
    assert true_false["answer"] == "O"

    fill_blank = create_problem(
        client,
        card_id,
        topic["id"],
        "트랜잭션의 네 가지 특성은 [빈칸], 일관성, 격리성, 지속성이다.",
        answer="원자성",
        problem_type="fill_blank",
    )
    assert fill_blank["problem_type"] == "fill_blank"
    assert fill_blank["choices"] is None
    assert fill_blank["answer"] == "원자성"


@pytest.mark.parametrize(
    "problem_type,choices,answer",
    [
        ("multiple_choice", None, None),
        ("multiple_choice", ["하나"], None),
        ("multiple_choice", [str(index) for index in range(11)], None),
        ("multiple_choice", [" 중복", "중복 "], None),
        ("multiple_choice", ["O", "X"], None),
        ("multiple_choice", ["O", "X"], "해당 없음"),
        ("true_false", None, None),
        ("true_false", ["O", "X"], "O"),
        ("true_false", None, "참"),
        ("short_answer", ["선택 1", "선택 2"], None),
        ("essay", ["선택 1", "선택 2"], None),
        ("fill_blank", ["선택 1", "선택 2"], None),
    ],
)
def test_rejects_invalid_problem_type_configuration(
    client: TestClient,
    problem_type: str,
    choices: list[str] | None,
    answer: str | None,
) -> None:
    card_id = create_card(client)
    topic = create_topic(client, card_id, "테스트")
    response = client.post(
        f"/cards/{card_id}/problems",
        json={
            "topic_id": topic["id"],
            "question": "유효한 문제인가?",
            "problem_type": problem_type,
            "choices": choices,
            "answer": answer,
        },
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "question",
    [
        "빈칸 표시가 없는 문장이다.",
        "[빈칸] 표시가 [빈칸] 두 개다.",
    ],
)
def test_fill_blank_requires_exactly_one_marker(
    client: TestClient,
    question: str,
) -> None:
    card_id = create_card(client)
    topic = create_topic(client, card_id, "테스트")
    response = client.post(
        f"/cards/{card_id}/problems",
        json={
            "topic_id": topic["id"],
            "question": question,
            "problem_type": "fill_blank",
            "answer": "정답",
        },
    )

    assert response.status_code == 422


def test_problem_patch_validates_merged_final_state(client: TestClient) -> None:
    card_id = create_card(client)
    topic = create_topic(client, card_id, "데이터베이스")
    problem = create_problem(
        client,
        card_id,
        topic["id"],
        "SQL 명령어는?",
        answer="SELECT",
        problem_type="multiple_choice",
        choices=["SELECT", "UPDATE"],
    )
    problem_url = f"/cards/{card_id}/problems/{problem['id']}"

    invalid_choices = client.patch(problem_url, json={"choices": ["INSERT", "DELETE"]})
    assert invalid_choices.status_code == 422
    unchanged = client.get(problem_url).json()
    assert unchanged["choices"] == ["SELECT", "UPDATE"]
    assert unchanged["answer"] == "SELECT"

    updated_choices = client.patch(
        problem_url,
        json={"choices": [" INSERT ", " DELETE "], "answer": " DELETE "},
    )
    assert updated_choices.status_code == 200
    assert updated_choices.json()["choices"] == ["INSERT", "DELETE"]
    assert updated_choices.json()["answer"] == "DELETE"

    type_without_clearing_choices = client.patch(problem_url, json={"problem_type": "essay"})
    assert type_without_clearing_choices.status_code == 422

    changed_type = client.patch(
        problem_url,
        json={"problem_type": "essay", "choices": None},
    )
    assert changed_type.status_code == 200
    assert changed_type.json()["problem_type"] == "essay"
    assert changed_type.json()["choices"] is None
    assert changed_type.json()["answer"] == "DELETE"


def test_problem_patch_requires_complete_valid_type_transition(client: TestClient) -> None:
    card_id = create_card(client)
    topic = create_topic(client, card_id, "네트워크")
    problem = create_problem(client, card_id, topic["id"], "HTTP란?")
    problem_url = f"/cards/{card_id}/problems/{problem['id']}"

    missing_choices = client.patch(problem_url, json={"problem_type": "multiple_choice"})
    assert missing_choices.status_code == 422

    valid_transition = client.patch(
        problem_url,
        json={
            "problem_type": "multiple_choice",
            "choices": ["프로토콜", "데이터베이스"],
            "answer": "프로토콜",
        },
    )
    assert valid_transition.status_code == 200
    assert valid_transition.json()["problem_type"] == "multiple_choice"
    assert valid_transition.json()["choices"] == ["프로토콜", "데이터베이스"]
