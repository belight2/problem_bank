from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models.graph_outbox import GraphOutboxEvent


def create_card(client: TestClient, title: str = "정보처리기사") -> dict:
    response = client.post("/cards", json={"title": title})
    assert response.status_code == 201
    return response.json()


def create_concept(client: TestClient, name: str) -> dict:
    response = client.post(
        "/concepts",
        json={"name": name, "description": f"{name} 설명"},
    )
    assert response.status_code == 201
    return response.json()


def attach_concept(client: TestClient, card_id: int, concept_id: int) -> None:
    response = client.put(f"/cards/{card_id}/concepts/{concept_id}")
    assert response.status_code == 200


def test_concept_crud_normalizes_names_and_reuses_concepts_across_cards(
    client: TestClient,
) -> None:
    first_card = create_card(client)
    second_card = create_card(client, "SQLD")
    concept = create_concept(client, "정규화")

    duplicate = client.post("/concepts", json={"name": "  정규화  "})
    assert duplicate.status_code == 409

    attach_concept(client, first_card["id"], concept["id"])
    attach_concept(client, second_card["id"], concept["id"])
    assert client.get(f"/cards/{first_card['id']}/concepts").json()[0]["id"] == concept["id"]
    assert client.get(f"/cards/{second_card['id']}/concepts").json()[0]["id"] == concept["id"]

    updated = client.patch(
        f"/concepts/{concept['id']}",
        json={"name": "데이터 정규화", "description": None},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "데이터 정규화"
    assert updated.json()["description"] is None

    assert client.delete(f"/concepts/{concept['id']}").status_code == 204
    assert client.get(f"/cards/{first_card['id']}/concepts").json() == []


def test_problem_and_note_concept_links_require_card_concepts(
    client: TestClient,
) -> None:
    card = create_card(client)
    topic = client.post(
        f"/cards/{card['id']}/topics",
        json={"name": "데이터베이스"},
    ).json()
    primary = create_concept(client, "정규화")
    supporting = create_concept(client, "함수 종속성")

    not_attached = client.post(
        f"/cards/{card['id']}/problems",
        json={
            "topic_id": topic["id"],
            "question": "정규화의 목적은?",
            "primary_concept_id": primary["id"],
        },
    )
    assert not_attached.status_code == 404

    attach_concept(client, card["id"], primary["id"])
    attach_concept(client, card["id"], supporting["id"])
    problem = client.post(
        f"/cards/{card['id']}/problems",
        json={
            "topic_id": topic["id"],
            "question": "정규화의 목적은?",
            "primary_concept_id": primary["id"],
            "supporting_concept_ids": [supporting["id"]],
        },
    )
    assert problem.status_code == 201
    assert problem.json()["primary_concept_id"] == primary["id"]
    assert problem.json()["supporting_concept_ids"] == [supporting["id"]]

    note = client.post(
        f"/cards/{card['id']}/notes",
        json={
            "title": "정규화 정리",
            "content_markdown": "# 정규화",
            "concept_ids": [primary["id"], supporting["id"]],
        },
    )
    assert note.status_code == 201
    assert set(note.json()["concept_ids"]) == {primary["id"], supporting["id"]}

    in_use = client.delete(f"/cards/{card['id']}/concepts/{primary['id']}")
    assert in_use.status_code == 409

    updated_problem = client.patch(
        f"/cards/{card['id']}/problems/{problem.json()['id']}",
        json={"primary_concept_id": None, "supporting_concept_ids": []},
    )
    assert updated_problem.status_code == 200
    assert updated_problem.json()["primary_concept_id"] is None
    updated_note = client.patch(
        f"/cards/{card['id']}/notes/{note.json()['id']}",
        json={"concept_ids": [supporting["id"]]},
    )
    assert updated_note.status_code == 200
    assert client.delete(f"/cards/{card['id']}/concepts/{primary['id']}").status_code == 204


def test_concept_relations_are_validated_and_enqueued(
    client: TestClient,
    test_session_factory: sessionmaker[Session],
) -> None:
    normalization = create_concept(client, "정규화")
    third_normal_form = create_concept(client, "제3정규형")

    self_relation = client.post(
        "/concept-relations",
        json={
            "source_concept_id": normalization["id"],
            "target_concept_id": normalization["id"],
            "relation_type": "related",
        },
    )
    assert self_relation.status_code == 422

    relation = client.post(
        "/concept-relations",
        json={
            "source_concept_id": third_normal_form["id"],
            "target_concept_id": normalization["id"],
            "relation_type": "broader",
        },
    )
    assert relation.status_code == 201
    assert relation.json()["source_concept_name"] == "제3정규형"
    assert relation.json()["target_concept_name"] == "정규화"

    duplicate = client.post(
        "/concept-relations",
        json={
            "source_concept_id": third_normal_form["id"],
            "target_concept_id": normalization["id"],
            "relation_type": "broader",
        },
    )
    assert duplicate.status_code == 409
    assert len(client.get("/concept-relations").json()) == 1

    with test_session_factory() as db:
        event = db.scalar(
            select(GraphOutboxEvent)
            .where(
                GraphOutboxEvent.aggregate_type == "concept",
                GraphOutboxEvent.aggregate_id == str(third_normal_form["id"]),
            )
            .order_by(GraphOutboxEvent.id.desc())
        )
        assert event is not None
        assert event.payload["entity"]["relations"] == [
            {
                "target_concept_id": normalization["id"],
                "relation_type": "broader",
            }
        ]

    assert client.delete(f"/concept-relations/{relation.json()['id']}").status_code == 204
    assert client.get("/concept-relations").json() == []
