from copy import deepcopy

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models.graph_outbox import GraphOutboxEvent


def create_exportable_card(client: TestClient) -> tuple[int, int, int]:
    card = client.post(
        "/cards",
        json={"title": "정보처리기사", "description": "시험 공부"},
    ).json()
    card_id = card["id"]
    topic = client.post(
        f"/cards/{card_id}/topics",
        json={"name": "데이터베이스"},
    ).json()
    normalization = client.post(
        "/concepts",
        json={"name": "정규화", "description": "중복을 줄이는 과정"},
    ).json()
    dependency = client.post(
        "/concepts",
        json={"name": "함수 종속성", "description": None},
    ).json()
    for concept in (normalization, dependency):
        response = client.put(f"/cards/{card_id}/concepts/{concept['id']}")
        assert response.status_code == 200
    relation = client.post(
        "/concept-relations",
        json={
            "source_concept_id": dependency["id"],
            "target_concept_id": normalization["id"],
            "relation_type": "prerequisite",
        },
    )
    assert relation.status_code == 201
    note = client.post(
        f"/cards/{card_id}/notes",
        json={
            "topic_id": topic["id"],
            "title": "정규화 정리",
            "content_markdown": "# 정규화\n\n함수 종속성을 확인한다.",
            "concept_ids": [normalization["id"], dependency["id"]],
        },
    ).json()
    problem = client.post(
        f"/cards/{card_id}/problems",
        json={
            "topic_id": topic["id"],
            "question": "정규화의 목적으로 가장 적절한 것은?",
            "problem_type": "multiple_choice",
            "choices": ["중복 감소", "중복 증가", "보안 해제", "백업 삭제", "인덱스 제거"],
            "answer": "중복 감소",
            "source_note_id": note["id"],
            "primary_concept_id": normalization["id"],
            "supporting_concept_ids": [dependency["id"]],
        },
    )
    assert problem.status_code == 201
    return card_id, normalization["id"], dependency["id"]


def test_card_package_export_preview_and_import(
    client: TestClient,
    test_session_factory: sessionmaker[Session],
) -> None:
    card_id, normalization_id, dependency_id = create_exportable_card(client)

    exported_response = client.get(f"/cards/{card_id}/package")
    assert exported_response.status_code == 200
    package = exported_response.json()
    assert package["format"] == "problem-bank-card"
    assert package["format_version"] == 1
    assert package["card"] == {
        "title": "정보처리기사",
        "description": "시험 공부",
    }
    assert [topic["name"] for topic in package["topics"]] == ["데이터베이스"]
    assert {concept["name"] for concept in package["concepts"]} == {
        "정규화",
        "함수 종속성",
    }
    assert len(package["concept_relations"]) == 1
    assert len(package["notes"]) == 1
    assert len(package["problems"]) == 1
    assert "presented_count" not in package["problems"][0]
    assert "correct_count" not in package["problems"][0]
    assert "incorrect_count" not in package["problems"][0]

    preview_response = client.post("/card-packages/preview", json=package)
    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["title"] == "정보처리기사"
    assert preview["summary"] == {
        "topic_count": 1,
        "concept_count": 2,
        "concept_relation_count": 1,
        "note_count": 1,
        "problem_count": 1,
    }
    assert preview["reused_concept_count"] == 2
    assert preview["new_concept_count"] == 0

    import_response = client.post("/card-packages/import", json=package)
    assert import_response.status_code == 201
    imported = import_response.json()
    imported_card_id = imported["card"]["id"]
    assert imported_card_id != card_id
    assert imported["summary"] == preview["summary"]

    imported_topics = client.get(f"/cards/{imported_card_id}/topics").json()
    imported_concepts = client.get(f"/cards/{imported_card_id}/concepts").json()
    imported_notes = client.get(f"/cards/{imported_card_id}/notes").json()
    imported_problems = client.get(f"/cards/{imported_card_id}/problems?limit=100").json()
    assert [topic["name"] for topic in imported_topics] == ["데이터베이스"]
    assert {concept["id"] for concept in imported_concepts} == {
        normalization_id,
        dependency_id,
    }
    assert imported_notes[0]["topic_id"] == imported_topics[0]["id"]
    assert set(imported_notes[0]["concept_ids"]) == {
        normalization_id,
        dependency_id,
    }
    assert imported_problems[0]["topic_id"] == imported_topics[0]["id"]
    assert imported_problems[0]["source_note_id"] == imported_notes[0]["id"]
    assert imported_problems[0]["primary_concept_id"] == normalization_id
    assert imported_problems[0]["supporting_concept_ids"] == [dependency_id]
    assert imported_problems[0]["presented_count"] == 0
    assert imported_problems[0]["correct_count"] == 0
    assert imported_problems[0]["incorrect_count"] == 0
    assert client.get(f"/cards/{imported_card_id}/workbooks").json() == []
    assert client.get(f"/cards/{imported_card_id}/wrong-answers").json() == []

    with test_session_factory() as db:
        imported_card_event = db.scalar(
            select(GraphOutboxEvent)
            .where(
                GraphOutboxEvent.aggregate_type == "card",
                GraphOutboxEvent.aggregate_id == str(imported_card_id),
            )
            .order_by(GraphOutboxEvent.id.desc())
        )
        assert imported_card_event is not None
        assert set(imported_card_event.payload["entity"]["concept_ids"]) == {
            normalization_id,
            dependency_id,
        }


def test_card_package_rejects_unknown_references_without_creating_card(
    client: TestClient,
) -> None:
    card_id, _, _ = create_exportable_card(client)
    package = client.get(f"/cards/{card_id}/package").json()
    invalid_package = deepcopy(package)
    invalid_package["problems"][0]["topic_ref"] = "topic:missing"
    before_ids = {card["id"] for card in client.get("/cards?limit=100").json()}

    assert client.post("/card-packages/preview", json=invalid_package).status_code == 422
    assert client.post("/card-packages/import", json=invalid_package).status_code == 422
    after_ids = {card["id"] for card in client.get("/cards?limit=100").json()}
    assert after_ids == before_ids


def test_card_package_import_creates_new_concepts_and_relations(
    client: TestClient,
    test_session_factory: sessionmaker[Session],
) -> None:
    card_id, _, _ = create_exportable_card(client)
    package = client.get(f"/cards/{card_id}/package").json()
    renamed_concepts = {
        "정규화": "정규화 복사본",
        "함수 종속성": "함수 종속성 복사본",
    }
    for concept in package["concepts"]:
        concept["name"] = renamed_concepts[concept["name"]]

    preview = client.post("/card-packages/preview", json=package).json()
    assert preview["reused_concept_count"] == 0
    assert preview["new_concept_count"] == 2

    imported = client.post("/card-packages/import", json=package)
    assert imported.status_code == 201
    imported_card_id = imported.json()["card"]["id"]
    imported_concepts = client.get(f"/cards/{imported_card_id}/concepts").json()
    concepts_by_name = {concept["name"]: concept for concept in imported_concepts}
    assert set(concepts_by_name) == set(renamed_concepts.values())

    relations = client.get("/concept-relations").json()
    copied_relation = next(
        relation
        for relation in relations
        if relation["source_concept_name"] == "함수 종속성 복사본"
    )
    assert copied_relation["target_concept_name"] == "정규화 복사본"
    assert copied_relation["relation_type"] == "prerequisite"

    with test_session_factory() as db:
        source_event = db.scalar(
            select(GraphOutboxEvent)
            .where(
                GraphOutboxEvent.aggregate_type == "concept",
                GraphOutboxEvent.aggregate_id == str(copied_relation["source_concept_id"]),
            )
            .order_by(GraphOutboxEvent.id.desc())
        )
        assert source_event is not None
        assert source_event.payload["entity"]["relations"] == [
            {
                "target_concept_id": copied_relation["target_concept_id"],
                "relation_type": "prerequisite",
            }
        ]


def test_card_package_rejects_unsupported_version(client: TestClient) -> None:
    card_id, _, _ = create_exportable_card(client)
    package = client.get(f"/cards/{card_id}/package").json()
    package["format_version"] = 2

    response = client.post("/card-packages/preview", json=package)
    assert response.status_code == 422
