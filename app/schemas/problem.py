from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models.problem import ProblemType

Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Choice = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Choices = Annotated[list[Choice], Field(min_length=2, max_length=10)]
TopicId = Annotated[int, Field(gt=0)]
FILL_BLANK_MARKER = "[빈칸]"


def validate_type_configuration(
    problem_type: ProblemType,
    choices: list[str] | None,
    answer: str | None,
) -> str | None:
    if problem_type is ProblemType.MULTIPLE_CHOICE:
        if choices is None:
            raise ValueError("Multiple-choice problems require choices")
        if len(choices) != len(set(choices)):
            raise ValueError("Choices must not contain duplicates")
        if answer is None:
            raise ValueError("Multiple-choice problems require an answer")
        normalized_answer = answer.strip()
        if normalized_answer not in choices:
            raise ValueError("Answer must be one of the choices")
        return normalized_answer

    if choices is not None:
        raise ValueError(f"{problem_type.value} problems cannot have choices")

    if problem_type is ProblemType.TRUE_FALSE:
        if answer is None:
            raise ValueError("True/false problems require an answer")
        normalized_answer = answer.strip()
        if normalized_answer not in {"O", "X"}:
            raise ValueError("True/false answer must be O or X")
        return normalized_answer

    return answer


class ProblemCreate(BaseModel):
    topic_id: TopicId
    question: Question
    problem_type: ProblemType = ProblemType.SHORT_ANSWER
    choices: Choices | None = None
    answer: str | None = None

    @model_validator(mode="after")
    def validate_configuration(self) -> Self:
        if (
            self.problem_type is ProblemType.FILL_BLANK
            and self.question.count(FILL_BLANK_MARKER) != 1
        ):
            raise ValueError("Fill-blank problems require exactly one [빈칸] marker")
        self.answer = validate_type_configuration(
            self.problem_type,
            self.choices,
            self.answer,
        )
        return self


class ProblemUpdate(BaseModel):
    topic_id: TopicId | None = None
    question: Question | None = None
    problem_type: ProblemType | None = None
    choices: Choices | None = None
    answer: str | None = None

    @model_validator(mode="after")
    def validate_changes(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if "topic_id" in self.model_fields_set and self.topic_id is None:
            raise ValueError("Topic ID cannot be null")
        if "question" in self.model_fields_set and self.question is None:
            raise ValueError("Question cannot be null")
        if "problem_type" in self.model_fields_set and self.problem_type is None:
            raise ValueError("Problem type cannot be null")
        return self


class ProblemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    card_id: int
    topic_id: int
    topic_name: str
    question: str
    problem_type: ProblemType
    choices: list[str] | None
    answer: str | None
    presented_count: int
    correct_count: int
    incorrect_count: int
    created_at: datetime
    updated_at: datetime


class RandomProblemSetRead(BaseModel):
    session_id: str | None
    problems: list[ProblemRead]


class StudyResultWrite(BaseModel):
    problem_id: int = Field(gt=0)
    result: Literal["correct", "incorrect", "ungraded"]


class StudyResultsWrite(BaseModel):
    results: list[StudyResultWrite] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_problem_ids(self) -> Self:
        problem_ids = [result.problem_id for result in self.results]
        if len(problem_ids) != len(set(problem_ids)):
            raise ValueError("Study results must not contain duplicate problem IDs")
        return self


class StudyResultsRead(BaseModel):
    status: Literal["recorded", "already_recorded"]
    problems: list[ProblemRead]
