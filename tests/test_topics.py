from fastapi.testclient import TestClient


def create_card(client: TestClient, title: str = "정보처리기사") -> int:
    response = client.post("/cards", json={"title": title})
    assert response.status_code == 201
    return response.json()["id"]


def create_topic(client: TestClient, card_id: int, name: str) -> dict:
    response = client.post(f"/cards/{card_id}/topics", json={"name": name})
    assert response.status_code == 201
    return response.json()


def test_topic_crud_and_name_normalization(client: TestClient) -> None:
    card_id = create_card(client)
    first_topic = create_topic(client, card_id, "  데이터베이스  ")
    second_topic = create_topic(client, card_id, "네트워크")
    assert first_topic["name"] == "데이터베이스"
    assert first_topic["card_id"] == card_id

    list_response = client.get(f"/cards/{card_id}/topics")
    assert list_response.status_code == 200
    assert [topic["id"] for topic in list_response.json()] == [
        first_topic["id"],
        second_topic["id"],
    ]

    get_response = client.get(f"/cards/{card_id}/topics/{first_topic['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "데이터베이스"

    update_response = client.patch(
        f"/cards/{card_id}/topics/{first_topic['id']}",
        json={"name": "  데이터 모델링  "},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "데이터 모델링"

    assert client.patch(f"/cards/{card_id}/topics/{first_topic['id']}", json={}).status_code == 422
    assert (
        client.patch(
            f"/cards/{card_id}/topics/{first_topic['id']}",
            json={"name": None},
        ).status_code
        == 422
    )

    delete_response = client.delete(f"/cards/{card_id}/topics/{first_topic['id']}")
    assert delete_response.status_code == 204
    assert client.get(f"/cards/{card_id}/topics/{first_topic['id']}").status_code == 404


def test_topic_name_is_unique_within_card(client: TestClient) -> None:
    first_card_id = create_card(client, "정보처리기사")
    second_card_id = create_card(client, "SQLD")
    create_topic(client, first_card_id, "Database")

    duplicate_create = client.post(
        f"/cards/{first_card_id}/topics",
        json={"name": "Database"},
    )
    assert duplicate_create.status_code == 409
    assert duplicate_create.json()["detail"] == "Topic name already exists"

    other_topic = create_topic(client, first_card_id, "Network")
    duplicate_update = client.patch(
        f"/cards/{first_card_id}/topics/{other_topic['id']}",
        json={"name": "Database"},
    )
    assert duplicate_update.status_code == 409
    assert duplicate_update.json()["detail"] == "Topic name already exists"

    case_variant = client.post(
        f"/cards/{first_card_id}/topics",
        json={"name": "database"},
    )
    assert case_variant.status_code == 201

    same_name_other_card = client.post(
        f"/cards/{second_card_id}/topics",
        json={"name": "Database"},
    )
    assert same_name_other_card.status_code == 201


def test_topic_is_scoped_to_its_card(client: TestClient) -> None:
    first_card_id = create_card(client, "정보처리기사")
    second_card_id = create_card(client, "SQLD")
    topic = create_topic(client, first_card_id, "데이터베이스")
    cross_card_url = f"/cards/{second_card_id}/topics/{topic['id']}"

    assert client.get(cross_card_url).status_code == 404
    assert client.patch(cross_card_url, json={"name": "수정 시도"}).status_code == 404
    assert client.delete(cross_card_url).status_code == 404
    assert client.get(f"/cards/{first_card_id}/topics/{topic['id']}").status_code == 200


def test_cannot_delete_topic_in_use(client: TestClient) -> None:
    card_id = create_card(client)
    topic = create_topic(client, card_id, "데이터베이스")
    problem_response = client.post(
        f"/cards/{card_id}/problems",
        json={"topic_id": topic["id"], "question": "기본키란?"},
    )
    assert problem_response.status_code == 201

    topic_url = f"/cards/{card_id}/topics/{topic['id']}"
    rename_response = client.patch(topic_url, json={"name": "관계형 데이터베이스"})
    assert rename_response.status_code == 200
    problem_id = problem_response.json()["id"]
    problem_after_rename = client.get(f"/cards/{card_id}/problems/{problem_id}")
    assert problem_after_rename.json()["topic_name"] == "관계형 데이터베이스"

    conflict_response = client.delete(topic_url)
    assert conflict_response.status_code == 409
    assert conflict_response.json()["detail"] == "Topic is in use"

    assert client.delete(f"/cards/{card_id}/problems/{problem_id}").status_code == 204
    assert client.delete(topic_url).status_code == 204


def test_topic_routes_require_existing_card(client: TestClient) -> None:
    assert client.get("/cards/999/topics").status_code == 404
    assert client.post("/cards/999/topics", json={"name": "주제"}).status_code == 404
