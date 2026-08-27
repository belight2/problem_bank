from datetime import datetime
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models.concept import ConceptRelationType

ConceptName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=120),
]
ConceptDescription = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
ConceptId = Annotated[int, Field(gt=0)]
ConceptIds = Annotated[list[ConceptId], Field(max_length=20)]


class ConceptCreate(BaseModel):
    name: ConceptName
    description: ConceptDescription | None = None


class ConceptUpdate(BaseModel):
    name: ConceptName | None = None
    description: ConceptDescription | None = None

    @model_validator(mode="after")
    def validate_changes(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Name cannot be null")
        return self


class ConceptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    profile_id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class ConceptRelationCreate(BaseModel):
    source_concept_id: ConceptId
    target_concept_id: ConceptId
    relation_type: ConceptRelationType

    @model_validator(mode="after")
    def validate_distinct_concepts(self) -> Self:
        if self.source_concept_id == self.target_concept_id:
            raise ValueError("A concept cannot be related to itself")
        return self


class ConceptRelationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_concept_id: int
    source_concept_name: str
    target_concept_id: int
    target_concept_name: str
    relation_type: ConceptRelationType
    created_at: datetime
