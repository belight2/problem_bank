from typing import Literal

from pydantic import BaseModel

KnowledgeGraphNodeType = Literal[
    "card",
    "topic",
    "problem",
    "note",
    "concept",
    "misconception",
    "unknown",
]


class KnowledgeGraphNodeRead(BaseModel):
    id: str
    iri: str
    type: KnowledgeGraphNodeType
    label: str
    external_id: int | None = None
    presented_count: int | None = None
    correct_count: int | None = None
    incorrect_count: int | None = None
    # 개념 노드 전용 숙련도(DB 집계). 다른 타입 노드에서는 None으로 남는다.
    attempted: bool | None = None
    problem_count: int | None = None
    mastery_score: float | None = None


class KnowledgeGraphEdgeRead(BaseModel):
    id: str
    source: str
    target: str
    type: str
    predicate: str
    label: str


class KnowledgeGraphRead(BaseModel):
    card_id: int
    nodes: list[KnowledgeGraphNodeRead]
    edges: list[KnowledgeGraphEdgeRead]
    truncated: bool
