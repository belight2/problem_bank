from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

PresetName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
ProblemCount = Annotated[int, Field(ge=1, le=100)]
TopicId = Annotated[int, Field(gt=0)]


class RandomStudyPresetWrite(BaseModel):
    name: PresetName
    description: str | None = None
    topic_id: TopicId | None = None
    problem_count: ProblemCount

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
    created_at: datetime
    updated_at: datetime
