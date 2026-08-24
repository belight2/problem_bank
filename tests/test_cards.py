from fastapi.testclient import TestClient


def test_card_crud(client: TestClient) -> None:
    create_response = client.post(
        "/cards",
        json={"title": "  정보처리기사  ", "description": "자격증 공부"},
    )
    assert create_response.status_code == 201
    created = create_response.json()
    card_id = created["id"]
    assert created["title"] == "정보처리기사"
    assert created["description"] == "자격증 공부"

    list_response = client.get("/cards")
    assert list_response.status_code == 200
    assert [card["id"] for card in list_response.json()] == [card_id]

    get_response = client.get(f"/cards/{card_id}")
    assert get_response.status_code == 200
    assert get_response.json()["title"] == "정보처리기사"

    update_response = client.patch(
        f"/cards/{card_id}",
        json={"title": "정보처리기사 필기", "description": None},
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "정보처리기사 필기"
    assert update_response.json()["description"] is None

    empty_update_response = client.patch(f"/cards/{card_id}", json={})
    assert empty_update_response.status_code == 422

    delete_response = client.delete(f"/cards/{card_id}")
    assert delete_response.status_code == 204
    assert client.get(f"/cards/{card_id}").status_code == 404


def test_card_not_found(client: TestClient) -> None:
    assert client.get("/cards/999").status_code == 404
