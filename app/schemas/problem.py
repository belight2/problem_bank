from datetime import datetime
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

Topic = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ProblemCreate(BaseModel):
    topic: Topic
    question: Question
    answer: str | None = None


class ProblemUpdate(BaseModel):
    topic: Topic | None = None
    question: Question | None = None
    answer: str | None = None

    @model_validator(mode="after")
    def validate_changes(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if "topic" in self.model_fields_set and self.topic is None:
            raise ValueError("Topic cannot be null")
        if "question" in self.model_fields_set and self.question is None:
            raise ValueError("Question cannot be null")
        return self


class ProblemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    card_id: int
    topic: str
    question: str
    answer: str | None
    created_at: datetime
    updated_at: datetime
