from fastapi.testclient import TestClient


def create_card_topic_problem(client: TestClient) -> tuple[int, dict, dict]:
    card_response = client.post("/cards", json={"title": "정보처리기사"})
    assert card_response.status_code == 201
    card_id = card_response.json()["id"]
    topic_response = client.post(
        f"/cards/{card_id}/topics",
        json={"name": "데이터베이스"},
    )
    assert topic_response.status_code == 201
    topic = topic_response.json()
    problem_response = client.post(
        f"/cards/{card_id}/problems",
        json={
            "topic_id": topic["id"],
            "question": "트랜잭션의 영속성이란?",
            "answer": "완료된 결과가 보존되는 성질",
        },
    )
    assert problem_response.status_code == 201
    return card_id, topic, problem_response.json()


def record_result(
    client: TestClient,
    card_id: int,
    problem_id: int,
    result: str,
    submitted_answer: str,
) -> dict:
    study_response = client.post(
        f"/cards/{card_id}/problems/random",
        params={"limit": 1},
    )
    assert study_response.status_code == 200
    session_id = study_response.json()["session_id"]
    response = client.post(
        f"/cards/{card_id}/problems/random/{session_id}/results",
        json={
            "results": [
                {
                    "problem_id": problem_id,
                    "result": result,
                    "submitted_answer": submitted_answer,
                }
            ]
        },
    )
    assert response.status_code == 200
    return response.json()


def test_incorrect_result_creates_and_updates_wrong_answer(client: TestClient) -> None:
    card_id, _topic, problem = create_card_topic_problem(client)

    recorded = record_result(
        client,
        card_id,
        problem["id"],
        "incorrect",
        "격리성",
    )
    assert recorded["status"] == "recorded"

    list_response = client.get(f"/cards/{card_id}/wrong-answers")
    assert list_response.status_code == 200
    wrong_answers = list_response.json()
    assert len(wrong_answers) == 1
    wrong_answer = wrong_answers[0]
    assert wrong_answer["problem_id"] == problem["id"]
    assert wrong_answer["status"] == "needs_review"
    assert wrong_answer["last_submitted_answer"] == "격리성"
    assert wrong_answer["problem"]["incorrect_count"] == 1
    assert wrong_answer["problem"]["topic_name"] == "데이터베이스"

    update_response = client.patch(
        f"/cards/{card_id}/wrong-answers/{problem['id']}",
        json={"status": "resolved", "memo": "영속성과 격리성을 구분한다."},
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "resolved"
    assert update_response.json()["memo"] == "영속성과 격리성을 구분한다."

    resolved_response = client.get(
        f"/cards/{card_id}/wrong-answers",
        params={"review_status": "resolved"},
    )
    assert [item["problem_id"] for item in resolved_response.json()] == [problem["id"]]
    assert client.get(
        f"/cards/{card_id}/wrong-answers",
        params={"review_status": "needs_review"},
    ).json() == []


def test_repeated_incorrect_result_reopens_resolved_wrong_answer(client: TestClient) -> None:
    card_id, _topic, problem = create_card_topic_problem(client)
    record_result(client, card_id, problem["id"], "incorrect", "첫 오답")
    assert client.patch(
        f"/cards/{card_id}/wrong-answers/{problem['id']}",
        json={"status": "resolved"},
    ).status_code == 200

    study_response = client.post(
        f"/cards/{card_id}/wrong-answers/study",
        params={"problem_id": problem["id"], "limit": 1},
    )
    assert study_response.status_code == 200
    session_id = study_response.json()["session_id"]
    record_url = f"/cards/{card_id}/problems/random/{session_id}/results"
    payload = {
        "results": [
            {
                "problem_id": problem["id"],
                "result": "incorrect",
                "submitted_answer": "두 번째 오답",
            }
        ]
    }
    assert client.post(record_url, json=payload).json()["status"] == "recorded"
    assert client.post(record_url, json=payload).json()["status"] == "already_recorded"

    wrong_answer = client.get(f"/cards/{card_id}/wrong-answers").json()[0]
    assert wrong_answer["status"] == "needs_review"
    assert wrong_answer["last_submitted_answer"] == "두 번째 오답"
    assert wrong_answer["problem"]["incorrect_count"] == 2


def test_wrong_answer_study_set_uses_unresolved_items(client: TestClient) -> None:
    card_id, _topic, problem = create_card_topic_problem(client)
    record_result(client, card_id, problem["id"], "incorrect", "오답")

    unresolved = client.post(
        f"/cards/{card_id}/wrong-answers/study",
        params={"limit": 10},
    )
    assert unresolved.status_code == 200
    assert [item["id"] for item in unresolved.json()["problems"]] == [problem["id"]]

    assert client.patch(
        f"/cards/{card_id}/wrong-answers/{problem['id']}",
        json={"status": "resolved"},
    ).status_code == 200
    resolved = client.post(
        f"/cards/{card_id}/wrong-answers/study",
        params={"limit": 10},
    )
    assert resolved.status_code == 200
    assert resolved.json() == {"session_id": None, "problems": []}


def test_wrong_answers_are_scoped_to_card(client: TestClient) -> None:
    card_id, _topic, problem = create_card_topic_problem(client)
    record_result(client, card_id, problem["id"], "incorrect", "오답")

    other_card = client.post("/cards", json={"title": "SQLD"}).json()
    assert client.get(f"/cards/{other_card['id']}/wrong-answers").json() == []
    assert client.patch(
        f"/cards/{other_card['id']}/wrong-answers/{problem['id']}",
        json={"memo": "잘못된 접근"},
    ).status_code == 404
    assert client.get("/cards/999/wrong-answers").status_code == 404
