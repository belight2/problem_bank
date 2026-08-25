from datetime import datetime
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

TopicName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]


class TopicCreate(BaseModel):
    name: TopicName


class TopicUpdate(BaseModel):
    name: TopicName | None = None

    @model_validator(mode="after")
    def validate_changes(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if self.name is None:
            raise ValueError("Name cannot be null")
        return self


class TopicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    card_id: int
    name: str
    created_at: datetime
    updated_at: datetime
