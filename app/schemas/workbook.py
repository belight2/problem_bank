from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.schemas.problem import ProblemRead

WorkbookTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=160),
]
SelectionMode = Literal["all", "incorrect_rate", "incorrect_count"]


class WorkbookCreate(BaseModel):
    title: WorkbookTitle | None = None
    topic_id: Annotated[int | None, Field(gt=0)] = None
    preset_id: Annotated[int | None, Field(gt=0)] = None
    problem_count: Annotated[int, Field(ge=1, le=100)] = 10
    selection_mode: SelectionMode = "all"
    incorrect_rate_threshold: Annotated[int, Field(ge=1, le=100)] = 50
    minimum_attempt_count: Annotated[int, Field(ge=1)] = 3
    incorrect_count_threshold: Annotated[int, Field(ge=1)] = 1


class WorkbookUpdate(BaseModel):
    title: WorkbookTitle | None = None

    @model_validator(mode="after")
    def validate_changes(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if self.title is None:
            raise ValueError("Title cannot be null")
        return self


class WorkbookRegenerate(BaseModel):
    title: WorkbookTitle | None = None


class WorkbookAttemptRead(BaseModel):
    id: str
    attempt_number: int
    status: Literal["in_progress", "completed"]
    correct_count: int
    incorrect_count: int
    ungraded_count: int
    created_at: datetime
    completed_at: datetime | None


class WorkbookRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    card_id: int
    title: str
    topic_id: int | None
    topic_name: str | None
    preset_id: int | None
    preset_name: str | None
    problem_count: int
    requested_problem_count: int
    selection_mode: SelectionMode
    incorrect_rate_threshold: int
    minimum_attempt_count: int
    incorrect_count_threshold: int
    attempts: list[WorkbookAttemptRead]
    created_at: datetime
    updated_at: datetime


class WorkbookStudyRead(BaseModel):
    workbook: WorkbookRead
    session_id: str
    problems: list[ProblemRead]
