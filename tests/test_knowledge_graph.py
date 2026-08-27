from typing import Any

import pytest
from fastapi.testclient import TestClient
from rdflib.plugins.sparql.parser import parseQuery

from app.api.dependencies import get_fuseki_client
from app.main import app
from app.services.fuseki import FusekiQueryError
from app.services.graph_rdf import PB_NAMESPACE, PBR_NAMESPACE
from app.services.knowledge_graph import (
    KnowledgeGraphResultError,
    build_card_knowledge_graph_query,
    load_card_knowledge_graph,
)


class FakeFusekiClient:
    def __init__(
        self,
        result: dict[str, Any] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result or {"results": {"bindings": []}}
        self.error = error
        self.queries: list[str] = []

    def query(self, sparql: str) -> dict[str, Any]:
        self.queries.append(sparql)
        if self.error is not None:
            raise self.error
        return self.result


def binding(value: str, *, binding_type: str = "uri") -> dict[str, str]:
    return {"type": binding_type, "value": value}


def relation_binding(
    *,
    source: str,
    source_type: str,
    source_label: str,
    predicate: str,
    target: str,
    target_type: str,
    target_label: str,
    source_external_id: int | None = None,
    presented_count: int | None = None,
    correct_count: int | None = None,
    incorrect_count: int | None = None,
) -> dict[str, dict[str, str]]:
    result = {
        "source": binding(source),
        "sourceType": binding(source_type),
        "sourceLabel": binding(source_label, binding_type="literal"),
        "predicate": binding(predicate),
        "target": binding(target),
        "targetType": binding(target_type),
        "targetLabel": binding(target_label, binding_type="literal"),
    }
    optional_values = {
        "sourceExternalId": source_external_id,
        "sourcePresentedCount": presented_count,
        "sourceCorrectCount": correct_count,
        "sourceIncorrectCount": incorrect_count,
    }
    for name, value in optional_values.items():
        if value is not None:
            result[name] = binding(str(value), binding_type="literal")
    return result


def test_build_card_knowledge_graph_query_is_valid_and_limited() -> None:
    query = build_card_knowledge_graph_query(7, 20)

    parseQuery(query)
    assert f"<{PBR_NAMESPACE}card-7>" in query
    assert f"<{PB_NAMESPACE}primaryConcept>" in query
    assert "LIMIT 21" in query


def test_load_card_knowledge_graph_normalizes_and_deduplicates_result() -> None:
    problem_iri = f"{PBR_NAMESPACE}problem-11"
    concept_iri = f"{PBR_NAMESPACE}concept/database"
    row = relation_binding(
        source=problem_iri,
        source_type=f"{PB_NAMESPACE}Problem",
        source_label="트랜잭션의 특징은?",
        predicate=f"{PB_NAMESPACE}primaryConcept",
        target=concept_iri,
        target_type=f"{PB_NAMESPACE}Concept",
        target_label="데이터베이스",
        source_external_id=11,
        presented_count=5,
        correct_count=3,
        incorrect_count=2,
    )
    client = FakeFusekiClient({"results": {"bindings": [row, row]}})

    graph = load_card_knowledge_graph(
        client,
        card_id=3,
        card_title="정보처리기사",
        limit=10,
    )

    assert graph.card_id == 3
    assert graph.truncated is False
    assert len(graph.nodes) == 3
    assert len(graph.edges) == 1

    nodes = {node.iri: node for node in graph.nodes}
    assert nodes[f"{PBR_NAMESPACE}card-3"].label == "정보처리기사"
    assert nodes[problem_iri].type == "problem"
    assert nodes[problem_iri].external_id == 11
    assert nodes[problem_iri].presented_count == 5
    assert nodes[problem_iri].correct_count == 3
    assert nodes[problem_iri].incorrect_count == 2
    assert nodes[concept_iri].type == "concept"

    edge = graph.edges[0]
    assert edge.source == problem_iri
    assert edge.target == concept_iri
    assert edge.type == "primary_concept"
    assert edge.label == "핵심 개념"


def test_load_card_knowledge_graph_reports_truncation() -> None:
    rows = [
        relation_binding(
            source=f"{PBR_NAMESPACE}problem-{problem_id}",
            source_type=f"{PB_NAMESPACE}Problem",
            source_label=f"문제 {problem_id}",
            predicate=f"{PB_NAMESPACE}inCard",
            target=f"{PBR_NAMESPACE}card-1",
            target_type=f"{PB_NAMESPACE}StudyCard",
            target_label="카드",
        )
        for problem_id in (1, 2)
    ]

    graph = load_card_knowledge_graph(
        FakeFusekiClient({"results": {"bindings": rows}}),
        card_id=1,
        card_title="카드",
        limit=1,
    )

    assert graph.truncated is True
    assert len(graph.edges) == 1


def test_load_card_knowledge_graph_rejects_malformed_result() -> None:
    with pytest.raises(KnowledgeGraphResultError):
        load_card_knowledge_graph(
            FakeFusekiClient({"unexpected": []}),
            card_id=1,
            card_title="카드",
            limit=10,
        )


def test_read_card_knowledge_graph(client: TestClient) -> None:
    card = client.post("/cards", json={"title": "정보처리기사"}).json()
    graph_client = FakeFusekiClient()
    app.dependency_overrides[get_fuseki_client] = lambda: graph_client

    response = client.get(f"/cards/{card['id']}/knowledge-graph?limit=25")

    assert response.status_code == 200
    assert response.json() == {
        "card_id": card["id"],
        "nodes": [
            {
                "id": f"{PBR_NAMESPACE}card-{card['id']}",
                "iri": f"{PBR_NAMESPACE}card-{card['id']}",
                "type": "card",
                "label": "정보처리기사",
                "external_id": card["id"],
                "presented_count": None,
                "correct_count": None,
                "incorrect_count": None,
            }
        ],
        "edges": [],
        "truncated": False,
    }
    assert len(graph_client.queries) == 1
    assert "LIMIT 26" in graph_client.queries[0]


def test_read_card_knowledge_graph_returns_404_before_query(client: TestClient) -> None:
    graph_client = FakeFusekiClient()
    app.dependency_overrides[get_fuseki_client] = lambda: graph_client

    response = client.get("/cards/999/knowledge-graph")

    assert response.status_code == 404
    assert graph_client.queries == []


def test_read_card_knowledge_graph_returns_503_when_fuseki_is_unavailable(
    client: TestClient,
) -> None:
    card = client.post("/cards", json={"title": "정보처리기사"}).json()
    app.dependency_overrides[get_fuseki_client] = lambda: FakeFusekiClient(
        error=FusekiQueryError("connection refused")
    )

    response = client.get(f"/cards/{card['id']}/knowledge-graph")

    assert response.status_code == 503
    assert response.json() == {"detail": "지식 그래프 저장소에 연결할 수 없습니다."}
