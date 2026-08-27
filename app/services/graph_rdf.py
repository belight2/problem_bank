import json
from collections.abc import Callable
from typing import Any

from app.models.graph_outbox import (
    GraphAggregateType,
    GraphOutboxEventType,
)

PB_NAMESPACE = "https://belight2.github.io/problem_bank/ontology#"
PBR_NAMESPACE = "https://belight2.github.io/problem_bank/resource/"

PREFIXES = f"""\
PREFIX pb: <{PB_NAMESPACE}>
PREFIX pbr: <{PBR_NAMESPACE}>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""

PROBLEM_TYPE_RESOURCES = {
    "short_answer": "pb:ShortAnswerProblemType",
    "essay": "pb:EssayProblemType",
    "multiple_choice": "pb:MultipleChoiceProblemType",
    "true_false": "pb:TrueFalseProblemType",
    "fill_blank": "pb:FillBlankProblemType",
}

CONCEPT_RELATION_PREDICATES = {
    "broader": "pb:broaderConcept",
    "prerequisite": "pb:prerequisiteOf",
    "related": "pb:relatedConcept",
    "contrasts": "pb:contrastsWith",
    "confused_with": "pb:commonlyConfusedWith",
}


def resource_iri(aggregate_type: str, aggregate_id: int) -> str:
    if aggregate_type not in {item.value for item in GraphAggregateType}:
        raise ValueError(f"지원하지 않는 그래프 엔티티 유형입니다: {aggregate_type}")
    if aggregate_id <= 0:
        raise ValueError("그래프 엔티티 ID는 양수여야 합니다.")
    return f"{PBR_NAMESPACE}{aggregate_type}-{aggregate_id}"


def sparql_string(value: str, *, language: str | None = None) -> str:
    literal = json.dumps(value, ensure_ascii=False)
    return f"{literal}@{language}" if language is not None else literal


def positive_integer(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name}는 양의 정수여야 합니다.")
    return value


def nonnegative_integer(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name}는 0 이상의 정수여야 합니다.")
    return value


def integer_list(value: Any, field_name: str) -> list[int]:
    # Concept fields were added after the first graph payload version. Treating a
    # missing field as an empty list keeps already queued Outbox events replayable.
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field_name}는 배열이어야 합니다.")
    values = [positive_integer(item, field_name) for item in value]
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name}에 중복된 ID가 있습니다.")
    return values


def required_string(entity: dict[str, Any], field_name: str) -> str:
    value = entity.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name}는 비어 있지 않은 문자열이어야 합니다.")
    return value


def card_triples(entity: dict[str, Any]) -> list[str]:
    card_id = positive_integer(entity.get("id"), "id")
    subject = f"pbr:card-{card_id}"
    triples = [
        f"{subject} a pb:StudyCard .",
        f'{subject} pb:externalId "{card_id}"^^xsd:positiveInteger .',
        f"{subject} rdfs:label {sparql_string(required_string(entity, 'title'), language='ko')} .",
    ]
    description = entity.get("description")
    if isinstance(description, str) and description:
        triples.append(
            f"{subject} dcterms:description {sparql_string(description, language='ko')} ."
        )
    for concept_id in integer_list(entity.get("concept_ids"), "concept_ids"):
        triples.append(f"{subject} pb:usesConcept pbr:concept-{concept_id} .")
    return triples


def topic_triples(entity: dict[str, Any]) -> list[str]:
    topic_id = positive_integer(entity.get("id"), "id")
    card_id = positive_integer(entity.get("card_id"), "card_id")
    subject = f"pbr:topic-{topic_id}"
    return [
        f"{subject} a pb:Topic .",
        f'{subject} pb:externalId "{topic_id}"^^xsd:positiveInteger .',
        f"{subject} pb:inCard pbr:card-{card_id} .",
        f"{subject} pb:topicOfCard pbr:card-{card_id} .",
        f"{subject} rdfs:label {sparql_string(required_string(entity, 'name'), language='ko')} .",
    ]


def problem_triples(entity: dict[str, Any]) -> list[str]:
    problem_id = positive_integer(entity.get("id"), "id")
    card_id = positive_integer(entity.get("card_id"), "card_id")
    topic_id = positive_integer(entity.get("topic_id"), "topic_id")
    problem_type = required_string(entity, "problem_type")
    problem_type_resource = PROBLEM_TYPE_RESOURCES.get(problem_type)
    if problem_type_resource is None:
        raise ValueError(f"지원하지 않는 문제 유형입니다: {problem_type}")

    subject = f"pbr:problem-{problem_id}"
    triples = [
        f"{subject} a pb:Problem .",
        f'{subject} pb:externalId "{problem_id}"^^xsd:positiveInteger .',
        f"{subject} pb:inCard pbr:card-{card_id} .",
        f"{subject} pb:classifiedUnder pbr:topic-{topic_id} .",
        f"{subject} pb:hasProblemType {problem_type_resource} .",
        f"{subject} rdfs:label "
        f"{sparql_string(required_string(entity, 'question'), language='ko')} .",
        f"{subject} pb:presentedCount "
        f'"{nonnegative_integer(entity.get("presented_count"), "presented_count")}"'
        "^^xsd:nonNegativeInteger .",
        f"{subject} pb:correctCount "
        f'"{nonnegative_integer(entity.get("correct_count"), "correct_count")}"'
        "^^xsd:nonNegativeInteger .",
        f"{subject} pb:incorrectCount "
        f'"{nonnegative_integer(entity.get("incorrect_count"), "incorrect_count")}"'
        "^^xsd:nonNegativeInteger .",
    ]
    source_note_id = entity.get("source_note_id")
    if source_note_id is not None:
        triples.append(
            f"{subject} pb:derivedFrom "
            f"pbr:note-{positive_integer(source_note_id, 'source_note_id')} ."
        )
    primary_concept_id = entity.get("primary_concept_id")
    if primary_concept_id is not None:
        triples.append(
            f"{subject} pb:primaryConcept "
            f"pbr:concept-{positive_integer(primary_concept_id, 'primary_concept_id')} ."
        )
    for concept_id in integer_list(
        entity.get("supporting_concept_ids"),
        "supporting_concept_ids",
    ):
        triples.append(f"{subject} pb:supportingConcept pbr:concept-{concept_id} .")
    return triples


def note_triples(entity: dict[str, Any]) -> list[str]:
    note_id = positive_integer(entity.get("id"), "id")
    card_id = positive_integer(entity.get("card_id"), "card_id")
    subject = f"pbr:note-{note_id}"
    triples = [
        f"{subject} a pb:Note .",
        f'{subject} pb:externalId "{note_id}"^^xsd:positiveInteger .',
        f"{subject} pb:inCard pbr:card-{card_id} .",
        f"{subject} rdfs:label {sparql_string(required_string(entity, 'title'), language='ko')} .",
    ]
    topic_id = entity.get("topic_id")
    if topic_id is not None:
        triples.append(
            f"{subject} pb:classifiedUnder pbr:topic-{positive_integer(topic_id, 'topic_id')} ."
        )
    for concept_id in integer_list(entity.get("concept_ids"), "concept_ids"):
        triples.append(f"{subject} pb:explains pbr:concept-{concept_id} .")
    return triples


def concept_triples(entity: dict[str, Any]) -> list[str]:
    concept_id = positive_integer(entity.get("id"), "id")
    subject = f"pbr:concept-{concept_id}"
    triples = [
        f"{subject} a pb:Concept .",
        f'{subject} pb:externalId "{concept_id}"^^xsd:positiveInteger .',
        f"{subject} rdfs:label {sparql_string(required_string(entity, 'name'), language='ko')} .",
    ]
    description = entity.get("description")
    if isinstance(description, str) and description:
        triples.append(
            f"{subject} dcterms:description {sparql_string(description, language='ko')} ."
        )
    relations = entity.get("relations", [])
    if not isinstance(relations, list):
        raise ValueError("relations는 배열이어야 합니다.")
    for relation in relations:
        if not isinstance(relation, dict):
            raise ValueError("relations 항목은 객체여야 합니다.")
        relation_type = required_string(relation, "relation_type")
        predicate = CONCEPT_RELATION_PREDICATES.get(relation_type)
        if predicate is None:
            raise ValueError(f"지원하지 않는 개념 관계 유형입니다: {relation_type}")
        target_id = positive_integer(relation.get("target_concept_id"), "target_concept_id")
        triples.append(f"{subject} {predicate} pbr:concept-{target_id} .")
    return triples


TRIPLE_BUILDERS: dict[str, Callable[[dict[str, Any]], list[str]]] = {
    GraphAggregateType.CARD.value: card_triples,
    GraphAggregateType.TOPIC.value: topic_triples,
    GraphAggregateType.PROBLEM.value: problem_triples,
    GraphAggregateType.NOTE.value: note_triples,
    GraphAggregateType.CONCEPT.value: concept_triples,
}

MANAGED_PREDICATES = {
    GraphAggregateType.CARD.value: (
        "rdf:type",
        "pb:externalId",
        "rdfs:label",
        "dcterms:description",
        "pb:usesConcept",
    ),
    GraphAggregateType.TOPIC.value: (
        "rdf:type",
        "pb:externalId",
        "pb:inCard",
        "pb:topicOfCard",
        "rdfs:label",
    ),
    GraphAggregateType.PROBLEM.value: (
        "rdf:type",
        "pb:externalId",
        "pb:inCard",
        "pb:classifiedUnder",
        "pb:hasProblemType",
        "rdfs:label",
        "pb:presentedCount",
        "pb:correctCount",
        "pb:incorrectCount",
        "pb:derivedFrom",
        "pb:primaryConcept",
        "pb:supportingConcept",
    ),
    GraphAggregateType.NOTE.value: (
        "rdf:type",
        "pb:externalId",
        "pb:inCard",
        "pb:classifiedUnder",
        "rdfs:label",
        "pb:explains",
    ),
    GraphAggregateType.CONCEPT.value: (
        "rdf:type",
        "pb:externalId",
        "rdfs:label",
        "dcterms:description",
        "pb:broaderConcept",
        "pb:prerequisiteOf",
        "pb:relatedConcept",
        "pb:contrastsWith",
        "pb:commonlyConfusedWith",
    ),
}


def build_upsert(aggregate_type: str, aggregate_id: int, entity: dict[str, Any]) -> str:
    builder = TRIPLE_BUILDERS.get(aggregate_type)
    if builder is None:
        raise ValueError(f"지원하지 않는 그래프 엔티티 유형입니다: {aggregate_type}")
    entity_id = positive_integer(entity.get("id"), "entity.id")
    if entity_id != aggregate_id:
        raise ValueError("Outbox aggregate_id와 payload의 ID가 일치하지 않습니다.")

    iri = resource_iri(aggregate_type, aggregate_id)
    triples = "\n  ".join(builder(entity))
    predicates = " ".join(MANAGED_PREDICATES[aggregate_type])
    return f"""\
{PREFIXES}
DELETE {{
  <{iri}> ?predicate ?object .
}}
WHERE {{
  VALUES ?predicate {{ {predicates} }}
  <{iri}> ?predicate ?object .
}} ;
INSERT DATA {{
  {triples}
}}
"""


def build_delete(aggregate_type: str, aggregate_id: int, entity: dict[str, Any]) -> str:
    iri = resource_iri(aggregate_type, aggregate_id)
    if aggregate_type == GraphAggregateType.CARD.value and entity.get("cascade") is True:
        return f"""\
{PREFIXES}
DELETE {{
  ?resource ?predicate ?object .
  ?incoming ?incomingPredicate ?resource .
}}
WHERE {{
  {{ BIND(<{iri}> AS ?resource) }}
  UNION
  {{ ?resource pb:inCard <{iri}> . }}
  ?resource ?predicate ?object .
  OPTIONAL {{ ?incoming ?incomingPredicate ?resource . }}
}}
"""
    return f"""\
{PREFIXES}
DELETE {{
  <{iri}> ?predicate ?object .
  ?incoming ?incomingPredicate <{iri}> .
}}
WHERE {{
  {{ <{iri}> ?predicate ?object . }}
  UNION
  {{ ?incoming ?incomingPredicate <{iri}> . }}
}}
"""


def build_graph_update(
    *,
    aggregate_type: str,
    aggregate_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> str:
    if payload.get("schema_version") != 1:
        raise ValueError("지원하지 않는 그래프 payload 버전입니다.")
    entity = payload.get("entity")
    if not isinstance(entity, dict):
        raise ValueError("그래프 payload에 entity 객체가 필요합니다.")
    try:
        numeric_id = int(aggregate_id)
    except ValueError as error:
        raise ValueError("aggregate_id는 정수 문자열이어야 합니다.") from error
    entity_id = positive_integer(entity.get("id"), "entity.id")
    if entity_id != numeric_id:
        raise ValueError("Outbox aggregate_id와 payload의 ID가 일치하지 않습니다.")

    if event_type == GraphOutboxEventType.UPSERT.value:
        return build_upsert(aggregate_type, numeric_id, entity)
    if event_type == GraphOutboxEventType.DELETE.value:
        return build_delete(aggregate_type, numeric_id, entity)
    raise ValueError(f"지원하지 않는 그래프 이벤트 유형입니다: {event_type}")
