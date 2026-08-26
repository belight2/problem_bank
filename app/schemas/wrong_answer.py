from datetime import datetime
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from app.models.wrong_answer import WrongAnswerStatus
from app.schemas.problem import ProblemRead

Memo = Annotated[str, StringConstraints(max_length=10000)]


class WrongAnswerUpdate(BaseModel):
    status: WrongAnswerStatus | None = None
    memo: Memo | None = None

    @model_validator(mode="after")
    def validate_changes(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if "status" in self.model_fields_set and self.status is None:
            raise ValueError("Status cannot be null")
        return self


class WrongAnswerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    card_id: int
    problem_id: int
    status: WrongAnswerStatus
    last_submitted_answer: str | None
    memo: str | None
    last_incorrect_at: datetime
    created_at: datetime
    updated_at: datetime
    problem: ProblemRead
