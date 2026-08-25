from fastapi.testclient import TestClient


def create_card(client: TestClient, title: str) -> int:
    response = client.post("/cards", json={"title": title, "description": None})
    assert response.status_code == 201
    return response.json()["id"]


def create_topic(client: TestClient, card_id: int, name: str) -> int:
    response = client.post(f"/cards/{card_id}/topics", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def test_random_study_settings_are_saved_per_card(client: TestClient) -> None:
    card_id = create_card(client, "정보처리기사")
    topic_id = create_topic(client, card_id, "데이터베이스")

    assert client.get(f"/cards/{card_id}/random-study-settings").json() is None

    create_response = client.put(
        f"/cards/{card_id}/random-study-settings",
        json={"problem_count": 20, "topic_id": topic_id},
    )
    assert create_response.status_code == 200
    assert create_response.json()["problem_count"] == 20
    assert create_response.json()["topic_id"] == topic_id

    update_response = client.put(
        f"/cards/{card_id}/random-study-settings",
        json={"problem_count": 5, "topic_id": None},
    )
    assert update_response.status_code == 200
    assert update_response.json()["problem_count"] == 5
    assert update_response.json()["topic_id"] is None

    saved = client.get(f"/cards/{card_id}/random-study-settings")
    assert saved.status_code == 200
    assert saved.json()["problem_count"] == 5
    assert saved.json()["topic_id"] is None


def test_random_study_settings_validate_card_topic_and_count(client: TestClient) -> None:
    card_id = create_card(client, "정보처리기사")
    other_card_id = create_card(client, "네트워크")
    other_topic_id = create_topic(client, other_card_id, "OSI")

    wrong_topic = client.put(
        f"/cards/{card_id}/random-study-settings",
        json={"problem_count": 10, "topic_id": other_topic_id},
    )
    assert wrong_topic.status_code == 404

    invalid_count = client.put(
        f"/cards/{card_id}/random-study-settings",
        json={"problem_count": 0, "topic_id": None},
    )
    assert invalid_count.status_code == 422
    assert client.get("/cards/999/random-study-settings").status_code == 404


def test_deleting_selected_topic_falls_back_to_card_scope(client: TestClient) -> None:
    card_id = create_card(client, "정보처리기사")
    topic_id = create_topic(client, card_id, "빈 주제")
    save_response = client.put(
        f"/cards/{card_id}/random-study-settings",
        json={"problem_count": 10, "topic_id": topic_id},
    )
    assert save_response.status_code == 200

    delete_response = client.delete(f"/cards/{card_id}/topics/{topic_id}")
    assert delete_response.status_code == 204

    saved = client.get(f"/cards/{card_id}/random-study-settings")
    assert saved.status_code == 200
    assert saved.json()["topic_id"] is None
