import unicodedata
from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models.concept import ConceptRelationType
from app.models.problem import ProblemType
from app.schemas.card import CardRead, CardTitle
from app.schemas.concept import ConceptDescription, ConceptName
from app.schemas.note import MarkdownContent, NoteTitle
from app.schemas.problem import FILL_BLANK_MARKER, Choices, Question, validate_type_configuration
from app.schemas.topic import TopicName

PackageReference = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
PackageDescription = Annotated[str, StringConstraints(max_length=10_000)]
PackageAnswer = Annotated[str, StringConstraints(max_length=10_000)]


class CardPackageModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CardPackageCard(CardPackageModel):
    title: CardTitle
    description: PackageDescription | None = None


class CardPackageTopic(CardPackageModel):
    ref: PackageReference
    name: TopicName


class CardPackageConcept(CardPackageModel):
    ref: PackageReference
    name: ConceptName
    description: ConceptDescription | None = None


class CardPackageConceptRelation(CardPackageModel):
    source_concept_ref: PackageReference
    target_concept_ref: PackageReference
    relation_type: ConceptRelationType


class CardPackageNote(CardPackageModel):
    ref: PackageReference
    topic_ref: PackageReference | None = None
    title: NoteTitle
    content_markdown: MarkdownContent
    concept_refs: list[PackageReference] = Field(default_factory=list, max_length=20)


class CardPackageProblem(CardPackageModel):
    topic_ref: PackageReference
    question: Question
    problem_type: ProblemType = ProblemType.SHORT_ANSWER
    choices: Choices | None = None
    answer: PackageAnswer | None = None
    source_note_ref: PackageReference | None = None
    primary_concept_ref: PackageReference | None = None
    supporting_concept_refs: list[PackageReference] = Field(
        default_factory=list,
        max_length=20,
    )

    @model_validator(mode="after")
    def validate_problem_configuration(self) -> Self:
        if self.primary_concept_ref in self.supporting_concept_refs:
            raise ValueError("Primary concept cannot also be a supporting concept")
        if len(self.supporting_concept_refs) != len(set(self.supporting_concept_refs)):
            raise ValueError("Supporting concept references must not contain duplicates")
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


class CardPackage(CardPackageModel):
    format: Literal["problem-bank-card"] = "problem-bank-card"
    format_version: Literal[1] = 1
    exported_at: datetime
    card: CardPackageCard
    topics: list[CardPackageTopic] = Field(default_factory=list, max_length=1_000)
    concepts: list[CardPackageConcept] = Field(default_factory=list, max_length=1_000)
    concept_relations: list[CardPackageConceptRelation] = Field(
        default_factory=list,
        max_length=5_000,
    )
    notes: list[CardPackageNote] = Field(default_factory=list, max_length=5_000)
    problems: list[CardPackageProblem] = Field(default_factory=list, max_length=10_000)

    @model_validator(mode="after")
    def validate_references(self) -> Self:
        topic_refs = [topic.ref for topic in self.topics]
        concept_refs = [concept.ref for concept in self.concepts]
        note_refs = [note.ref for note in self.notes]
        if len(topic_refs) != len(set(topic_refs)):
            raise ValueError("Topic references must be unique")
        if len(concept_refs) != len(set(concept_refs)):
            raise ValueError("Concept references must be unique")
        if len(note_refs) != len(set(note_refs)):
            raise ValueError("Note references must be unique")
        topic_names = [topic.name for topic in self.topics]
        if len(topic_names) != len(set(topic_names)):
            raise ValueError("Topic names must be unique")
        concept_name_keys = [
            unicodedata.normalize("NFKC", concept.name).casefold() for concept in self.concepts
        ]
        if len(concept_name_keys) != len(set(concept_name_keys)):
            raise ValueError("Concept names must be unique")

        topic_ref_set = set(topic_refs)
        concept_ref_set = set(concept_refs)
        note_ref_set = set(note_refs)
        for note in self.notes:
            if note.topic_ref is not None and note.topic_ref not in topic_ref_set:
                raise ValueError(f"Unknown topic reference: {note.topic_ref}")
            unknown_concepts = set(note.concept_refs) - concept_ref_set
            if unknown_concepts:
                raise ValueError(f"Unknown concept reference: {sorted(unknown_concepts)[0]}")
            if len(note.concept_refs) != len(set(note.concept_refs)):
                raise ValueError("Note concept references must not contain duplicates")

        for problem in self.problems:
            if problem.topic_ref not in topic_ref_set:
                raise ValueError(f"Unknown topic reference: {problem.topic_ref}")
            if problem.source_note_ref is not None and problem.source_note_ref not in note_ref_set:
                raise ValueError(f"Unknown note reference: {problem.source_note_ref}")
            problem_concept_refs = set(problem.supporting_concept_refs)
            if problem.primary_concept_ref is not None:
                problem_concept_refs.add(problem.primary_concept_ref)
            unknown_concepts = problem_concept_refs - concept_ref_set
            if unknown_concepts:
                raise ValueError(f"Unknown concept reference: {sorted(unknown_concepts)[0]}")

        relation_keys: set[tuple[str, str, str]] = set()
        symmetric_relations = {
            ConceptRelationType.RELATED,
            ConceptRelationType.CONTRASTS,
            ConceptRelationType.CONFUSED_WITH,
        }
        for relation in self.concept_relations:
            if relation.source_concept_ref not in concept_ref_set:
                raise ValueError(f"Unknown concept reference: {relation.source_concept_ref}")
            if relation.target_concept_ref not in concept_ref_set:
                raise ValueError(f"Unknown concept reference: {relation.target_concept_ref}")
            if relation.source_concept_ref == relation.target_concept_ref:
                raise ValueError("A concept cannot be related to itself")
            source_ref = relation.source_concept_ref
            target_ref = relation.target_concept_ref
            if relation.relation_type in symmetric_relations and source_ref > target_ref:
                source_ref, target_ref = target_ref, source_ref
            relation_key = (source_ref, target_ref, relation.relation_type.value)
            if relation_key in relation_keys:
                raise ValueError("Concept relations must not contain duplicates")
            relation_keys.add(relation_key)
        return self


class CardPackageSummary(CardPackageModel):
    topic_count: int
    concept_count: int
    concept_relation_count: int
    note_count: int
    problem_count: int


class CardPackagePreview(CardPackageModel):
    format_version: int
    title: str
    summary: CardPackageSummary
    reused_concept_count: int
    new_concept_count: int


class CardPackageImportRead(CardPackageModel):
    card: CardRead
    summary: CardPackageSummary
    reused_concept_count: int
    new_concept_count: int
