from datetime import datetime
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.schemas.concept import ConceptIds

NoteTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]
MarkdownContent = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
TopicId = Annotated[int, Field(gt=0)]


class NoteCreate(BaseModel):
    title: NoteTitle
    content_markdown: MarkdownContent
    topic_id: TopicId | None = None
    concept_ids: ConceptIds = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_concepts(self) -> Self:
        if len(self.concept_ids) != len(set(self.concept_ids)):
            raise ValueError("Concept IDs must not contain duplicates")
        return self


class NoteUpdate(BaseModel):
    title: NoteTitle | None = None
    content_markdown: MarkdownContent | None = None
    topic_id: TopicId | None = None
    concept_ids: ConceptIds | None = None

    @model_validator(mode="after")
    def validate_changes(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("Title cannot be null")
        if "content_markdown" in self.model_fields_set and self.content_markdown is None:
            raise ValueError("Markdown content cannot be null")
        if "concept_ids" in self.model_fields_set and self.concept_ids is None:
            raise ValueError("Concept IDs cannot be null")
        return self


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    card_id: int
    topic_id: int | None
    topic_name: str | None
    title: str
    content_markdown: str
    concept_ids: list[int]
    created_at: datetime
    updated_at: datetime
