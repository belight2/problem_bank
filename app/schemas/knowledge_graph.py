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
