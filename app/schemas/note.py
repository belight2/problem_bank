from datetime import datetime
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

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


class NoteUpdate(BaseModel):
    title: NoteTitle | None = None
    content_markdown: MarkdownContent | None = None
    topic_id: TopicId | None = None

    @model_validator(mode="after")
    def validate_changes(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("Title cannot be null")
        if "content_markdown" in self.model_fields_set and self.content_markdown is None:
            raise ValueError("Markdown content cannot be null")
        return self


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    card_id: int
    topic_id: int | None
    topic_name: str | None
    title: str
    content_markdown: str
    created_at: datetime
    updated_at: datetime
