from fastapi.testclient import TestClient


def create_card(client: TestClient, title: str) -> int:
    response = client.post("/cards", json={"title": title, "description": None})
    assert response.status_code == 201
    return response.json()["id"]


def create_topic(client: TestClient, card_id: int, name: str) -> int:
    response = client.post(f"/cards/{card_id}/topics", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def create_preset(
    client: TestClient,
    card_id: int,
    *,
    name: str,
    topic_id: int | None,
    problem_count: int,
    description: str | None = None,
    selection_mode: str = "all",
    incorrect_rate_threshold: int = 50,
    minimum_attempt_count: int = 3,
    incorrect_count_threshold: int = 1,
) -> dict:
    response = client.post(
        f"/cards/{card_id}/random-study-presets",
        json={
            "name": name,
            "description": description,
            "topic_id": topic_id,
            "problem_count": problem_count,
            "selection_mode": selection_mode,
            "incorrect_rate_threshold": incorrect_rate_threshold,
            "minimum_attempt_count": minimum_attempt_count,
            "incorrect_count_threshold": incorrect_count_threshold,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_random_study_preset_crud(client: TestClient) -> None:
    card_id = create_card(client, "정보처리기사")
    topic_id = create_topic(client, card_id, "데이터베이스")
    preset = create_preset(
        client,
        card_id,
        name="DB 20문제",
        description="데이터베이스 집중 학습",
        topic_id=topic_id,
        problem_count=20,
    )

    listed = client.get(f"/cards/{card_id}/random-study-presets")
    assert listed.status_code == 200
    assert listed.json() == [preset]

    updated = client.put(
        f"/cards/{card_id}/random-study-presets/{preset['id']}",
        json={
            "name": "DB 짧게",
            "description": "  ",
            "topic_id": None,
            "problem_count": 5,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "DB 짧게"
    assert updated.json()["description"] is None
    assert updated.json()["topic_id"] is None
    assert updated.json()["problem_count"] == 5

    deleted = client.delete(
        f"/cards/{card_id}/random-study-presets/{preset['id']}"
    )
    assert deleted.status_code == 204
    assert client.get(f"/cards/{card_id}/random-study-presets").json() == []


def test_random_study_preset_validates_name_topic_and_count(client: TestClient) -> None:
    card_id = create_card(client, "정보처리기사")
    other_card_id = create_card(client, "네트워크")
    other_topic_id = create_topic(client, other_card_id, "OSI")
    create_preset(
        client,
        card_id,
        name="전체",
        topic_id=None,
        problem_count=10,
    )

    duplicate = client.post(
        f"/cards/{card_id}/random-study-presets",
        json={
            "name": "전체",
            "description": None,
            "topic_id": None,
            "problem_count": 5,
        },
    )
    assert duplicate.status_code == 409

    wrong_topic = client.post(
        f"/cards/{card_id}/random-study-presets",
        json={
            "name": "잘못된 주제",
            "description": None,
            "topic_id": other_topic_id,
            "problem_count": 5,
        },
    )
    assert wrong_topic.status_code == 404

    invalid_count = client.post(
        f"/cards/{card_id}/random-study-presets",
        json={
            "name": "잘못된 개수",
            "description": None,
            "topic_id": None,
            "problem_count": 101,
        },
    )
    assert invalid_count.status_code == 422


def test_applying_preset_uses_its_values(client: TestClient) -> None:
    card_id = create_card(client, "정보처리기사")
    topic_id = create_topic(client, card_id, "데이터베이스")
    preset = create_preset(
        client,
        card_id,
        name="DB 15문제",
        topic_id=topic_id,
        problem_count=15,
        selection_mode="incorrect_count",
        incorrect_count_threshold=3,
    )

    applied = client.put(
        f"/cards/{card_id}/random-study-settings",
        json={
            "preset_id": preset["id"],
            "topic_id": None,
            "problem_count": 1,
        },
    )
    assert applied.status_code == 200
    assert applied.json()["preset_id"] == preset["id"]
    assert applied.json()["topic_id"] == topic_id
    assert applied.json()["problem_count"] == 15
    assert applied.json()["selection_mode"] == "incorrect_count"
    assert applied.json()["incorrect_count_threshold"] == 3


def test_active_preset_update_and_delete_keep_settings_consistent(
    client: TestClient,
) -> None:
    card_id = create_card(client, "정보처리기사")
    topic_id = create_topic(client, card_id, "데이터베이스")
    preset = create_preset(
        client,
        card_id,
        name="기본",
        topic_id=None,
        problem_count=10,
    )
    applied = client.put(
        f"/cards/{card_id}/random-study-settings",
        json={
            "preset_id": preset["id"],
            "topic_id": None,
            "problem_count": 10,
        },
    )
    assert applied.status_code == 200

    updated = client.put(
        f"/cards/{card_id}/random-study-presets/{preset['id']}",
        json={
            "name": "기본",
            "description": "변경됨",
            "topic_id": topic_id,
            "problem_count": 7,
        },
    )
    assert updated.status_code == 200
    saved = client.get(f"/cards/{card_id}/random-study-settings").json()
    assert saved["preset_id"] == preset["id"]
    assert saved["topic_id"] == topic_id
    assert saved["problem_count"] == 7

    deleted = client.delete(
        f"/cards/{card_id}/random-study-presets/{preset['id']}"
    )
    assert deleted.status_code == 204
    saved_after_delete = client.get(
        f"/cards/{card_id}/random-study-settings"
    ).json()
    assert saved_after_delete["preset_id"] is None
    assert saved_after_delete["topic_id"] == topic_id
    assert saved_after_delete["problem_count"] == 7
