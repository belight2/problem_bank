from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

PresetName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
ProblemCount = Annotated[int, Field(ge=1, le=100)]
TopicId = Annotated[int, Field(gt=0)]
SelectionMode = Literal["all", "incorrect_rate", "incorrect_count"]
IncorrectRateThreshold = Annotated[int, Field(ge=1, le=100)]
PositiveCount = Annotated[int, Field(ge=1)]


class RandomStudyPresetWrite(BaseModel):
    name: PresetName
    description: str | None = None
    topic_id: TopicId | None = None
    problem_count: ProblemCount
    selection_mode: SelectionMode = "all"
    incorrect_rate_threshold: IncorrectRateThreshold = 50
    minimum_attempt_count: PositiveCount = 3
    incorrect_count_threshold: PositiveCount = 1

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class RandomStudyPresetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    card_id: int
    name: str
    description: str | None
    topic_id: int | None
    problem_count: int
    selection_mode: SelectionMode
    incorrect_rate_threshold: int
    minimum_attempt_count: int
    incorrect_count_threshold: int
    created_at: datetime
    updated_at: datetime
