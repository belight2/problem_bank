from fastapi.testclient import TestClient


def create_card(client: TestClient, title: str = "정보처리기사") -> int:
    response = client.post("/cards", json={"title": title})
    assert response.status_code == 201
    return response.json()["id"]


def create_topic(client: TestClient, card_id: int, name: str = "데이터베이스") -> int:
    response = client.post(f"/cards/{card_id}/topics", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def create_problem(client: TestClient, card_id: int, topic_id: int, question: str) -> int:
    response = client.post(
        f"/cards/{card_id}/problems",
        json={"topic_id": topic_id, "question": question, "answer": "답"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_workbook_keeps_problem_order_and_attempt_history(client: TestClient) -> None:
    card_id = create_card(client)
    topic_id = create_topic(client, card_id)
    problem_ids = {
        create_problem(client, card_id, topic_id, "첫 문제"),
        create_problem(client, card_id, topic_id, "둘째 문제"),
        create_problem(client, card_id, topic_id, "셋째 문제"),
    }

    created = client.post(
        f"/cards/{card_id}/workbooks",
        json={
            "title": "데이터베이스 기본 문제집",
            "topic_id": topic_id,
            "problem_count": 2,
            "selection_mode": "all",
        },
    )
    assert created.status_code == 201
    created_payload = created.json()
    workbook = created_payload["workbook"]
    selected_ids = [problem["id"] for problem in created_payload["problems"]]
    assert workbook["title"] == "데이터베이스 기본 문제집"
    assert workbook["problem_count"] == 2
    assert workbook["topic_name"] == "데이터베이스"
    assert set(selected_ids).issubset(problem_ids)
    assert workbook["attempts"][0]["status"] == "in_progress"
    assert workbook["attempts"][0]["attempt_number"] == 1

    results = [
        {
            "problem_id": selected_ids[0],
            "result": "correct",
            "submitted_answer": "답",
        },
        {
            "problem_id": selected_ids[1],
            "result": "incorrect",
            "submitted_answer": "오답",
        },
    ]
    recorded = client.post(
        f"/cards/{card_id}/workbooks/{workbook['id']}"
        f"/attempts/{created_payload['session_id']}/results",
        json={"results": results},
    )
    assert recorded.status_code == 200

    listed = client.get(f"/cards/{card_id}/workbooks")
    assert listed.status_code == 200
    first_attempt = listed.json()[0]["attempts"][0]
    assert first_attempt["status"] == "completed"
    assert first_attempt["correct_count"] == 1
    assert first_attempt["incorrect_count"] == 1

    replayed = client.post(
        f"/cards/{card_id}/workbooks/{workbook['id']}/attempts"
    )
    assert replayed.status_code == 200
    replay_payload = replayed.json()
    assert [problem["id"] for problem in replay_payload["problems"]] == selected_ids
    assert replay_payload["workbook"]["attempts"][0]["attempt_number"] == 2
    assert replay_payload["workbook"]["attempts"][0]["status"] == "in_progress"


def test_workbook_can_regenerate_rename_and_delete(client: TestClient) -> None:
    card_id = create_card(client)
    topic_id = create_topic(client, card_id)
    for index in range(4):
        create_problem(client, card_id, topic_id, f"문제 {index}")

    source = client.post(
        f"/cards/{card_id}/workbooks",
        json={"title": "원본 문제집", "topic_id": topic_id, "problem_count": 3},
    ).json()["workbook"]

    regenerated = client.post(
        f"/cards/{card_id}/workbooks/{source['id']}/regenerate",
        json={"title": "새 문제집"},
    )
    assert regenerated.status_code == 201
    regenerated_workbook = regenerated.json()["workbook"]
    assert regenerated_workbook["id"] != source["id"]
    assert regenerated_workbook["title"] == "새 문제집"
    assert regenerated_workbook["topic_id"] == topic_id
    assert regenerated_workbook["requested_problem_count"] == 3

    renamed = client.patch(
        f"/cards/{card_id}/workbooks/{source['id']}",
        json={"title": "수정된 문제집"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "수정된 문제집"

    deleted = client.delete(f"/cards/{card_id}/workbooks/{source['id']}")
    assert deleted.status_code == 204
    assert client.get(f"/cards/{card_id}/workbooks/{source['id']}").status_code == 404


def test_workbook_is_scoped_and_rejects_empty_selection(client: TestClient) -> None:
    first_card_id = create_card(client)
    second_card_id = create_card(client, "SQLD")
    topic_id = create_topic(client, first_card_id)
    create_problem(client, first_card_id, topic_id, "기본키란?")
    workbook_id = client.post(
        f"/cards/{first_card_id}/workbooks",
        json={"topic_id": topic_id, "problem_count": 1},
    ).json()["workbook"]["id"]

    assert client.get(f"/cards/{second_card_id}/workbooks/{workbook_id}").status_code == 404
    assert (
        client.post(f"/cards/{second_card_id}/workbooks/{workbook_id}/attempts").status_code
        == 404
    )

    empty = client.post(
        f"/cards/{first_card_id}/workbooks",
        json={
            "problem_count": 10,
            "selection_mode": "incorrect_count",
            "incorrect_count_threshold": 5,
        },
    )
    assert empty.status_code == 422
    assert empty.json()["detail"] == "설정한 출제 기준에 맞는 문제가 없습니다."
