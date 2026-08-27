from typing import Any

import pytest
from rdflib.plugins.sparql.parser import parseUpdate

from app.services.graph_rdf import build_graph_update


@pytest.mark.parametrize(
    "aggregate_type,aggregate_id,entity,expected_fragments",
    [
        (
            "card",
            "1",
            {
                "id": 1,
                "profile_id": 1,
                "title": "정보처리기사",
                "description": "자격증 공부",
            },
            ["a pb:StudyCard", 'rdfs:label "정보처리기사"@ko'],
        ),
        (
            "topic",
            "2",
            {"id": 2, "card_id": 1, "name": "데이터베이스"},
            ["a pb:Topic", "pb:topicOfCard pbr:card-1"],
        ),
        (
            "problem",
            "3",
            {
                "id": 3,
                "card_id": 1,
                "topic_id": 2,
                "question": '정규화의 "목적"은?',
                "problem_type": "short_answer",
                "source_note_id": 4,
                "presented_count": 5,
                "correct_count": 3,
                "incorrect_count": 2,
            },
            [
                "a pb:Problem",
                "pb:derivedFrom pbr:note-4",
                'pb:presentedCount "5"^^xsd:nonNegativeInteger',
                '\\"목적\\"',
            ],
        ),
        (
            "note",
            "4",
            {"id": 4, "card_id": 1, "topic_id": None, "title": "정규화 정리"},
            ["a pb:Note", 'rdfs:label "정규화 정리"@ko'],
        ),
    ],
)
def test_build_upsert_graph_update(
    aggregate_type: str,
    aggregate_id: str,
    entity: dict[str, Any],
    expected_fragments: list[str],
) -> None:
    update = build_graph_update(
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        event_type="upsert",
        payload={"schema_version": 1, "entity": entity},
    )

    parseUpdate(update)
    for fragment in expected_fragments:
        assert fragment in update
    assert "answer" not in update
    assert "content_markdown" not in update


def test_card_delete_cascades_only_card_scoped_resources() -> None:
    update = build_graph_update(
        aggregate_type="card",
        aggregate_id="1",
        event_type="delete",
        payload={
            "schema_version": 1,
            "entity": {"id": 1, "cascade": True},
        },
    )

    parseUpdate(update)
    assert "?resource pb:inCard" in update
    assert "?resource ?predicate ?object" in update


def test_graph_update_rejects_mismatched_payload_id() -> None:
    with pytest.raises(ValueError, match="일치하지 않습니다"):
        build_graph_update(
            aggregate_type="topic",
            aggregate_id="2",
            event_type="upsert",
            payload={
                "schema_version": 1,
                "entity": {"id": 3, "card_id": 1, "name": "데이터베이스"},
            },
        )


def test_delete_graph_update_rejects_mismatched_payload_id() -> None:
    with pytest.raises(ValueError, match="일치하지 않습니다"):
        build_graph_update(
            aggregate_type="card",
            aggregate_id="1",
            event_type="delete",
            payload={
                "schema_version": 1,
                "entity": {"id": 2, "cascade": True},
            },
        )
