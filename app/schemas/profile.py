from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

ProfileName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=80),
]


class ProfileWrite(BaseModel):
    display_name: ProfileName
    timezone: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
    daily_goal: Annotated[int, Field(ge=1, le=100)] = 20

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("Unknown timezone") from error
        return value


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str
    timezone: str
    daily_goal: int
    is_configured: bool
    created_at: datetime
    updated_at: datetime
