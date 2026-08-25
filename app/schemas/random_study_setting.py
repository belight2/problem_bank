from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

ProblemCount = Annotated[int, Field(ge=1, le=100)]
TopicId = Annotated[int, Field(gt=0)]


class RandomStudySettingUpdate(BaseModel):
    problem_count: ProblemCount
    topic_id: TopicId | None = None


class RandomStudySettingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    card_id: int
    topic_id: int | None
    problem_count: int
    created_at: datetime
    updated_at: datetime
