import unicodedata

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.concept import (
    CardConcept,
    Concept,
    NoteConcept,
    ProblemConcept,
    ProblemConceptRole,
)
from app.models.note import Note
from app.models.problem import Problem


def concept_name_key(name: str) -> str:
    return unicodedata.normalize("NFKC", name).casefold()


def get_card_concepts_by_id(
    db: Session,
    card_id: int,
    concept_ids: list[int],
) -> dict[int, Concept]:
    unique_ids = set(concept_ids)
    if not unique_ids:
        return {}
    concepts = list(
        db.scalars(
            select(Concept)
            .join(CardConcept)
            .where(
                CardConcept.card_id == card_id,
                Concept.id.in_(unique_ids),
            )
        )
    )
    concepts_by_id = {concept.id: concept for concept in concepts}
    if concepts_by_id.keys() != unique_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Concept not found in card",
        )
    return concepts_by_id


def set_problem_concepts(
    db: Session,
    problem: Problem,
    *,
    primary_concept_id: int | None,
    supporting_concept_ids: list[int],
) -> None:
    desired_roles = {
        concept_id: ProblemConceptRole.SUPPORTING.value for concept_id in supporting_concept_ids
    }
    if primary_concept_id is not None:
        desired_roles[primary_concept_id] = ProblemConceptRole.PRIMARY.value
    get_card_concepts_by_id(db, problem.card_id, list(desired_roles))

    links_by_id = {link.concept_id: link for link in problem.concept_links}
    for link in list(problem.concept_links):
        if link.concept_id not in desired_roles:
            problem.concept_links.remove(link)
    for concept_id, role in desired_roles.items():
        link = links_by_id.get(concept_id)
        if link is None:
            problem.concept_links.append(ProblemConcept(concept_id=concept_id, role=role))
        else:
            link.role = role


def set_note_concepts(db: Session, note: Note, concept_ids: list[int]) -> None:
    get_card_concepts_by_id(db, note.card_id, concept_ids)
    desired_ids = set(concept_ids)
    existing_ids = {link.concept_id for link in note.concept_links}
    for link in list(note.concept_links):
        if link.concept_id not in desired_ids:
            note.concept_links.remove(link)
    for concept_id in desired_ids - existing_ids:
        note.concept_links.append(NoteConcept(concept_id=concept_id))
