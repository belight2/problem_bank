from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

ProblemCount = Annotated[int, Field(ge=1, le=100)]
TopicId = Annotated[int, Field(gt=0)]
PresetId = Annotated[int, Field(gt=0)]
SelectionMode = Literal["all", "incorrect_rate", "incorrect_count"]
IncorrectRateThreshold = Annotated[int, Field(ge=1, le=100)]
PositiveCount = Annotated[int, Field(ge=1)]


class RandomStudySettingUpdate(BaseModel):
    problem_count: ProblemCount
    topic_id: TopicId | None = None
    preset_id: PresetId | None = None
    selection_mode: SelectionMode = "all"
    incorrect_rate_threshold: IncorrectRateThreshold = 50
    minimum_attempt_count: PositiveCount = 3
    incorrect_count_threshold: PositiveCount = 1


class RandomStudySettingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    card_id: int
    topic_id: int | None
    preset_id: int | None
    problem_count: int
    selection_mode: SelectionMode
    incorrect_rate_threshold: int
    minimum_attempt_count: int
    incorrect_count_threshold: int
    created_at: datetime
    updated_at: datetime
