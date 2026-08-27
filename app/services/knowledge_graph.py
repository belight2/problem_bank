from hashlib import sha256
from typing import Any, Protocol
from urllib.parse import unquote

from app.schemas.knowledge_graph import (
    KnowledgeGraphEdgeRead,
    KnowledgeGraphNodeRead,
    KnowledgeGraphNodeType,
    KnowledgeGraphRead,
)
from app.services.graph_rdf import PB_NAMESPACE, PREFIXES, resource_iri

NODE_TYPES: dict[str, KnowledgeGraphNodeType] = {
    f"{PB_NAMESPACE}StudyCard": "card",
    f"{PB_NAMESPACE}Topic": "topic",
    f"{PB_NAMESPACE}Problem": "problem",
    f"{PB_NAMESPACE}Note": "note",
    f"{PB_NAMESPACE}Concept": "concept",
    f"{PB_NAMESPACE}Misconception": "misconception",
}

RELATIONS: dict[str, tuple[str, str]] = {
    f"{PB_NAMESPACE}inCard": ("in_card", "카드 소속"),
    f"{PB_NAMESPACE}classifiedUnder": ("classified_under", "주제 분류"),
    f"{PB_NAMESPACE}derivedFrom": ("derived_from", "노트에서 파생"),
    f"{PB_NAMESPACE}usesConcept": ("uses_concept", "개념 사용"),
    f"{PB_NAMESPACE}organizesConcept": ("organizes_concept", "개념 분류"),
    f"{PB_NAMESPACE}assesses": ("assesses", "개념 평가"),
    f"{PB_NAMESPACE}primaryConcept": ("primary_concept", "핵심 개념"),
    f"{PB_NAMESPACE}supportingConcept": ("supporting_concept", "보조 개념"),
    f"{PB_NAMESPACE}explains": ("explains", "개념 설명"),
    f"{PB_NAMESPACE}broaderConcept": ("broader_concept", "상위 개념"),
    f"{PB_NAMESPACE}prerequisiteOf": ("prerequisite_of", "선수 개념"),
    f"{PB_NAMESPACE}relatedConcept": ("related_concept", "관련 개념"),
    f"{PB_NAMESPACE}contrastsWith": ("contrasts_with", "대조 개념"),
    f"{PB_NAMESPACE}commonlyConfusedWith": (
        "commonly_confused_with",
        "혼동 개념",
    ),
    f"{PB_NAMESPACE}misconceptionAbout": (
        "misconception_about",
        "오개념 대상",
    ),
    f"{PB_NAMESPACE}addressesMisconception": (
        "addresses_misconception",
        "오개념 다룸",
    ),
    f"{PB_NAMESPACE}correctsMisconception": (
        "corrects_misconception",
        "오개념 교정",
    ),
}


class SparqlQueryClient(Protocol):
    def query(self, sparql: str) -> dict[str, Any]: ...


class KnowledgeGraphResultError(RuntimeError):
    pass


def build_card_knowledge_graph_query(card_id: int, limit: int) -> str:
    if card_id <= 0:
        raise ValueError("card_id는 양수여야 합니다.")
    if limit <= 0:
        raise ValueError("limit은 양수여야 합니다.")

    card_iri = resource_iri("card", card_id)
    relation_values = "\n    ".join(f"<{predicate}>" for predicate in RELATIONS)
    node_type_values = "\n    ".join(f"<{node_type}>" for node_type in NODE_TYPES)
    return f"""\
{PREFIXES}
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT
  ?source ?sourceType ?sourceLabel ?sourceExternalId
  ?sourcePresentedCount ?sourceCorrectCount ?sourceIncorrectCount
  ?predicate
  ?target ?targetType ?targetLabel ?targetExternalId
  ?targetPresentedCount ?targetCorrectCount ?targetIncorrectCount
WHERE {{
  VALUES ?predicate {{
    {relation_values}
  }}
  VALUES ?sourceType {{
    {node_type_values}
  }}
  VALUES ?targetType {{
    {node_type_values}
  }}

  ?source a ?sourceType ;
          ?predicate ?target .
  ?target a ?targetType .

  FILTER (
    ?source = <{card_iri}> ||
    ?target = <{card_iri}> ||
    EXISTS {{ ?source pb:inCard <{card_iri}> }} ||
    EXISTS {{ ?target pb:inCard <{card_iri}> }} ||
    EXISTS {{ <{card_iri}> pb:usesConcept ?source }} ||
    EXISTS {{ <{card_iri}> pb:usesConcept ?target }} ||
    EXISTS {{
      VALUES ?sourceLink {{
        pb:organizesConcept pb:assesses pb:primaryConcept pb:supportingConcept
        pb:explains pb:addressesMisconception pb:correctsMisconception
      }}
      ?sourceMember pb:inCard <{card_iri}> ;
                    ?sourceLink ?source .
    }} ||
    EXISTS {{
      VALUES ?targetLink {{
        pb:organizesConcept pb:assesses pb:primaryConcept pb:supportingConcept
        pb:explains pb:addressesMisconception pb:correctsMisconception
      }}
      ?targetMember pb:inCard <{card_iri}> ;
                    ?targetLink ?target .
    }}
  )

  OPTIONAL {{
    ?source rdfs:label ?sourceRdfsLabel .
    FILTER (LANG(?sourceRdfsLabel) = "" || LANGMATCHES(LANG(?sourceRdfsLabel), "ko"))
  }}
  OPTIONAL {{
    ?source skos:prefLabel ?sourceSkosLabel .
    FILTER (LANG(?sourceSkosLabel) = "" || LANGMATCHES(LANG(?sourceSkosLabel), "ko"))
  }}
  BIND(COALESCE(?sourceRdfsLabel, ?sourceSkosLabel) AS ?sourceLabel)
  OPTIONAL {{ ?source pb:externalId ?sourceExternalId }}
  OPTIONAL {{ ?source pb:presentedCount ?sourcePresentedCount }}
  OPTIONAL {{ ?source pb:correctCount ?sourceCorrectCount }}
  OPTIONAL {{ ?source pb:incorrectCount ?sourceIncorrectCount }}

  OPTIONAL {{
    ?target rdfs:label ?targetRdfsLabel .
    FILTER (LANG(?targetRdfsLabel) = "" || LANGMATCHES(LANG(?targetRdfsLabel), "ko"))
  }}
  OPTIONAL {{
    ?target skos:prefLabel ?targetSkosLabel .
    FILTER (LANG(?targetSkosLabel) = "" || LANGMATCHES(LANG(?targetSkosLabel), "ko"))
  }}
  BIND(COALESCE(?targetRdfsLabel, ?targetSkosLabel) AS ?targetLabel)
  OPTIONAL {{ ?target pb:externalId ?targetExternalId }}
  OPTIONAL {{ ?target pb:presentedCount ?targetPresentedCount }}
  OPTIONAL {{ ?target pb:correctCount ?targetCorrectCount }}
  OPTIONAL {{ ?target pb:incorrectCount ?targetIncorrectCount }}
}}
ORDER BY ?source ?predicate ?target
LIMIT {limit + 1}
"""


def load_card_knowledge_graph(
    client: SparqlQueryClient,
    *,
    card_id: int,
    card_title: str,
    limit: int,
) -> KnowledgeGraphRead:
    result = client.query(build_card_knowledge_graph_query(card_id, limit))
    bindings = _bindings(result)
    truncated = len(bindings) > limit

    card_iri = resource_iri("card", card_id)
    nodes: dict[str, KnowledgeGraphNodeRead] = {
        card_iri: KnowledgeGraphNodeRead(
            id=card_iri,
            iri=card_iri,
            type="card",
            label=card_title,
            external_id=card_id,
        )
    }
    edges: dict[tuple[str, str, str], KnowledgeGraphEdgeRead] = {}

    for binding in bindings[:limit]:
        if not isinstance(binding, dict):
            raise KnowledgeGraphResultError("Fuseki 결과의 binding 형식이 올바르지 않습니다.")
        source = _required_binding(binding, "source")
        target = _required_binding(binding, "target")
        predicate = _required_binding(binding, "predicate")
        relation = RELATIONS.get(predicate)
        if relation is None:
            continue

        if source not in nodes:
            nodes[source] = _node_from_binding(binding, "source", source)
        if target not in nodes:
            nodes[target] = _node_from_binding(binding, "target", target)

        edge_key = (source, predicate, target)
        if edge_key not in edges:
            relation_type, relation_label = relation
            edge_hash = sha256("\0".join(edge_key).encode()).hexdigest()[:20]
            edges[edge_key] = KnowledgeGraphEdgeRead(
                id=f"edge-{edge_hash}",
                source=source,
                target=target,
                type=relation_type,
                predicate=predicate,
                label=relation_label,
            )

    return KnowledgeGraphRead(
        card_id=card_id,
        nodes=list(nodes.values()),
        edges=list(edges.values()),
        truncated=truncated,
    )


def _bindings(result: dict[str, Any]) -> list[Any]:
    result_set = result.get("results")
    if not isinstance(result_set, dict):
        raise KnowledgeGraphResultError("Fuseki 결과에 results 객체가 없습니다.")
    bindings = result_set.get("bindings")
    if not isinstance(bindings, list):
        raise KnowledgeGraphResultError("Fuseki 결과에 bindings 배열이 없습니다.")
    return bindings


def _node_from_binding(
    binding: dict[str, Any],
    prefix: str,
    iri: str,
) -> KnowledgeGraphNodeRead:
    class_iri = _optional_binding(binding, f"{prefix}Type")
    node_type = NODE_TYPES.get(class_iri or "", "unknown")
    return KnowledgeGraphNodeRead(
        id=iri,
        iri=iri,
        type=node_type,
        label=_optional_binding(binding, f"{prefix}Label") or _fallback_label(iri),
        external_id=_optional_nonnegative_integer(binding, f"{prefix}ExternalId"),
        presented_count=_optional_nonnegative_integer(binding, f"{prefix}PresentedCount"),
        correct_count=_optional_nonnegative_integer(binding, f"{prefix}CorrectCount"),
        incorrect_count=_optional_nonnegative_integer(binding, f"{prefix}IncorrectCount"),
    )


def _required_binding(binding: dict[str, Any], name: str) -> str:
    value = _optional_binding(binding, name)
    if value is None:
        raise KnowledgeGraphResultError(f"Fuseki 결과에 {name} 값이 없습니다.")
    return value


def _optional_binding(binding: dict[str, Any], name: str) -> str | None:
    item = binding.get(name)
    if item is None:
        return None
    if not isinstance(item, dict):
        raise KnowledgeGraphResultError(f"Fuseki 결과의 {name} 형식이 올바르지 않습니다.")
    value = item.get("value")
    if not isinstance(value, str) or not value:
        raise KnowledgeGraphResultError(f"Fuseki 결과의 {name} 값이 올바르지 않습니다.")
    return value


def _optional_nonnegative_integer(
    binding: dict[str, Any],
    name: str,
) -> int | None:
    value = _optional_binding(binding, name)
    if value is None:
        return None
    try:
        numeric_value = int(value)
    except ValueError as error:
        raise KnowledgeGraphResultError(f"Fuseki 결과의 {name} 값이 정수가 아닙니다.") from error
    if numeric_value < 0:
        raise KnowledgeGraphResultError(f"Fuseki 결과의 {name} 값이 음수입니다.")
    return numeric_value


def _fallback_label(iri: str) -> str:
    return unquote(iri.rstrip("/").rsplit("/", 1)[-1].rsplit("#", 1)[-1])
