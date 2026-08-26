from fastapi.testclient import TestClient


def create_card(client: TestClient, title: str = "정보처리기사") -> int:
    response = client.post("/cards", json={"title": title})
    assert response.status_code == 201
    return response.json()["id"]


def create_topic(client: TestClient, card_id: int, name: str = "데이터베이스") -> int:
    response = client.post(f"/cards/{card_id}/topics", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def create_note(
    client: TestClient,
    card_id: int,
    *,
    title: str = "정규화 정리",
    content_markdown: str = "# 정규화\n\n중복을 줄이는 과정",
    topic_id: int | None = None,
) -> dict:
    response = client.post(
        f"/cards/{card_id}/notes",
        json={
            "title": title,
            "content_markdown": content_markdown,
            "topic_id": topic_id,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_note_crud_with_optional_topic(client: TestClient) -> None:
    card_id = create_card(client)
    topic_id = create_topic(client, card_id)
    note = create_note(client, card_id, topic_id=topic_id)

    assert note["title"] == "정규화 정리"
    assert note["content_markdown"].startswith("# 정규화")
    assert note["topic_id"] == topic_id
    assert note["topic_name"] == "데이터베이스"

    listed = client.get(f"/cards/{card_id}/notes")
    assert listed.status_code == 200
    assert listed.json() == [note]

    updated = client.patch(
        f"/cards/{card_id}/notes/{note['id']}",
        json={
            "title": "정규화와 이상 현상",
            "content_markdown": "## 이상 현상\n\n- 삽입\n- 수정\n- 삭제",
            "topic_id": None,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "정규화와 이상 현상"
    assert updated.json()["topic_id"] is None
    assert updated.json()["topic_name"] is None

    assert client.patch(f"/cards/{card_id}/notes/{note['id']}", json={}).status_code == 422
    deleted = client.delete(f"/cards/{card_id}/notes/{note['id']}")
    assert deleted.status_code == 204
    assert client.get(f"/cards/{card_id}/notes/{note['id']}").status_code == 404


def test_note_and_topic_must_belong_to_requested_card(client: TestClient) -> None:
    first_card_id = create_card(client, "정보처리기사")
    second_card_id = create_card(client, "SQLD")
    second_topic_id = create_topic(client, second_card_id, "SQL")
    note = create_note(client, first_card_id)

    wrong_topic = client.post(
        f"/cards/{first_card_id}/notes",
        json={
            "title": "잘못된 주제",
            "content_markdown": "내용",
            "topic_id": second_topic_id,
        },
    )
    assert wrong_topic.status_code == 404
    assert client.get(f"/cards/{second_card_id}/notes/{note['id']}").status_code == 404
    assert client.get("/cards/999/notes").status_code == 404


def test_problem_can_reference_note_and_survives_note_deletion(client: TestClient) -> None:
    card_id = create_card(client)
    topic_id = create_topic(client, card_id)
    note = create_note(client, card_id, topic_id=topic_id)

    problem_response = client.post(
        f"/cards/{card_id}/problems",
        json={
            "topic_id": topic_id,
            "question": "정규화의 목적은?",
            "source_note_id": note["id"],
        },
    )
    assert problem_response.status_code == 201
    problem = problem_response.json()
    assert problem["source_note_id"] == note["id"]
    assert problem["source_note_title"] == note["title"]

    assert client.delete(f"/cards/{card_id}/notes/{note['id']}").status_code == 204
    saved_problem = client.get(f"/cards/{card_id}/problems/{problem['id']}")
    assert saved_problem.status_code == 200
    assert saved_problem.json()["source_note_id"] is None
    assert saved_problem.json()["source_note_title"] is None


def test_problem_cannot_reference_note_from_another_card(client: TestClient) -> None:
    first_card_id = create_card(client, "정보처리기사")
    second_card_id = create_card(client, "SQLD")
    topic_id = create_topic(client, first_card_id)
    other_note = create_note(client, second_card_id)

    response = client.post(
        f"/cards/{first_card_id}/problems",
        json={
            "topic_id": topic_id,
            "question": "잘못된 출처 노트인가?",
            "source_note_id": other_note["id"],
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Note not found"


def test_deleting_note_topic_keeps_note_without_topic(client: TestClient) -> None:
    card_id = create_card(client)
    topic_id = create_topic(client, card_id)
    note = create_note(client, card_id, topic_id=topic_id)

    assert client.delete(f"/cards/{card_id}/topics/{topic_id}").status_code == 204
    saved_note = client.get(f"/cards/{card_id}/notes/{note['id']}")
    assert saved_note.status_code == 200
    assert saved_note.json()["topic_id"] is None
    assert saved_note.json()["topic_name"] is None
