from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.dependencies import CurrentProfile, DatabaseSession
from app.api.routes.cards import get_card_or_404
from app.models.card import Card
from app.models.concept import (
    CardConcept,
    Concept,
    ConceptRelation,
    ConceptRelationType,
    NoteConcept,
    ProblemConcept,
)
from app.models.graph_outbox import GraphOutboxEventType
from app.models.note import Note
from app.models.problem import Problem
from app.schemas.concept import (
    ConceptCreate,
    ConceptRead,
    ConceptRelationCreate,
    ConceptRelationRead,
    ConceptUpdate,
)
from app.services.concepts import concept_name_key
from app.services.graph_outbox import enqueue_card_event, enqueue_concept_event

router = APIRouter(tags=["concepts"])

SYMMETRIC_RELATIONS = {
    ConceptRelationType.RELATED.value,
    ConceptRelationType.CONTRASTS.value,
    ConceptRelationType.CONFUSED_WITH.value,
}


def get_concept_or_404(concept_id: int, profile_id: int, db: DatabaseSession) -> Concept:
    concept = db.scalar(
        select(Concept)
        .options(
            selectinload(Concept.card_links),
            selectinload(Concept.outgoing_relations),
        )
        .where(Concept.id == concept_id, Concept.profile_id == profile_id)
    )
    if concept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found")
    return concept


def ensure_unique_concept_name(
    db: DatabaseSession,
    profile_id: int,
    name: str,
    *,
    exclude_id: int | None = None,
) -> str:
    name_key = concept_name_key(name)
    statement = select(Concept.id).where(
        Concept.profile_id == profile_id,
        Concept.name_key == name_key,
    )
    if exclude_id is not None:
        statement = statement.where(Concept.id != exclude_id)
    if db.scalar(statement) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="같은 이름의 개념이 이미 있습니다.",
        )
    return name_key


@router.get("/concepts", response_model=list[ConceptRead])
def list_concepts(
    db: DatabaseSession,
    profile: CurrentProfile,
    query: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
) -> list[Concept]:
    statement = select(Concept).where(Concept.profile_id == profile.id)
    if query is not None:
        statement = statement.where(func.lower(Concept.name).contains(query.casefold()))
    return list(db.scalars(statement.order_by(Concept.name, Concept.id)))


@router.post("/concepts", response_model=ConceptRead, status_code=status.HTTP_201_CREATED)
def create_concept(
    payload: ConceptCreate,
    db: DatabaseSession,
    profile: CurrentProfile,
) -> Concept:
    concept = Concept(
        profile=profile,
        name=payload.name,
        name_key=ensure_unique_concept_name(db, profile.id, payload.name),
        description=payload.description,
    )
    db.add(concept)
    db.flush()
    enqueue_concept_event(db, concept)
    db.commit()
    db.refresh(concept)
    return concept


@router.patch("/concepts/{concept_id}", response_model=ConceptRead)
def update_concept(
    concept_id: int,
    payload: ConceptUpdate,
    db: DatabaseSession,
    profile: CurrentProfile,
) -> Concept:
    concept = get_concept_or_404(concept_id, profile.id, db)
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes:
        concept.name_key = ensure_unique_concept_name(
            db,
            profile.id,
            changes["name"],
            exclude_id=concept.id,
        )
    for field, value in changes.items():
        setattr(concept, field, value)
    enqueue_concept_event(db, concept)
    db.commit()
    db.refresh(concept)
    return concept


@router.delete("/concepts/{concept_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_concept(
    concept_id: int,
    db: DatabaseSession,
    profile: CurrentProfile,
) -> Response:
    concept = get_concept_or_404(concept_id, profile.id, db)
    enqueue_concept_event(db, concept, event_type=GraphOutboxEventType.DELETE)
    db.delete(concept)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/cards/{card_id}/concepts", response_model=list[ConceptRead])
def list_card_concepts(
    card_id: int,
    db: DatabaseSession,
    profile: CurrentProfile,
) -> list[Concept]:
    get_card_or_404(card_id, db, profile.id)
    return list(
        db.scalars(
            select(Concept)
            .join(CardConcept)
            .where(CardConcept.card_id == card_id)
            .order_by(Concept.name, Concept.id)
        )
    )


@router.put("/cards/{card_id}/concepts/{concept_id}", response_model=ConceptRead)
def attach_concept_to_card(
    card_id: int,
    concept_id: int,
    db: DatabaseSession,
    profile: CurrentProfile,
) -> Concept:
    card = db.scalar(
        select(Card)
        .options(selectinload(Card.concept_links))
        .where(Card.id == card_id, Card.profile_id == profile.id)
    )
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    concept = get_concept_or_404(concept_id, profile.id, db)
    if all(link.concept_id != concept_id for link in card.concept_links):
        card.concept_links.append(CardConcept(concept=concept))
        db.flush()
        enqueue_card_event(db, card)
        db.commit()
    return concept


@router.delete(
    "/cards/{card_id}/concepts/{concept_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def detach_concept_from_card(
    card_id: int,
    concept_id: int,
    db: DatabaseSession,
    profile: CurrentProfile,
) -> Response:
    card = db.scalar(
        select(Card)
        .options(selectinload(Card.concept_links))
        .where(Card.id == card_id, Card.profile_id == profile.id)
    )
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    link = next(
        (link for link in card.concept_links if link.concept_id == concept_id),
        None,
    )
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not in card")
    is_used = db.scalar(
        select(
            or_(
                select(ProblemConcept.problem_id)
                .join(Problem)
                .where(
                    Problem.card_id == card_id,
                    ProblemConcept.concept_id == concept_id,
                )
                .exists(),
                select(NoteConcept.note_id)
                .join(Note)
                .where(
                    Note.card_id == card_id,
                    NoteConcept.concept_id == concept_id,
                )
                .exists(),
            )
        )
    )
    if is_used:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="문제나 노트에서 사용 중인 개념은 카드에서 해제할 수 없습니다.",
        )
    card.concept_links.remove(link)
    db.flush()
    enqueue_card_event(db, card)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/concept-relations", response_model=list[ConceptRelationRead])
def list_concept_relations(
    db: DatabaseSession,
    profile: CurrentProfile,
) -> list[ConceptRelation]:
    return list(
        db.scalars(
            select(ConceptRelation)
            .join(Concept, Concept.id == ConceptRelation.source_concept_id)
            .options(
                selectinload(ConceptRelation.source_concept),
                selectinload(ConceptRelation.target_concept),
            )
            .where(Concept.profile_id == profile.id)
            .order_by(ConceptRelation.id)
        )
    )


@router.post(
    "/concept-relations",
    response_model=ConceptRelationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_concept_relation(
    payload: ConceptRelationCreate,
    db: DatabaseSession,
    profile: CurrentProfile,
) -> ConceptRelation:
    source_id = payload.source_concept_id
    target_id = payload.target_concept_id
    if payload.relation_type.value in SYMMETRIC_RELATIONS and source_id > target_id:
        source_id, target_id = target_id, source_id
    source = get_concept_or_404(source_id, profile.id, db)
    target = get_concept_or_404(target_id, profile.id, db)
    existing = db.scalar(
        select(ConceptRelation.id).where(
            ConceptRelation.source_concept_id == source_id,
            ConceptRelation.target_concept_id == target_id,
            ConceptRelation.relation_type == payload.relation_type.value,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="같은 개념 관계가 이미 있습니다.",
        )
    relation = ConceptRelation(
        source_concept=source,
        target_concept=target,
        relation_type=payload.relation_type.value,
    )
    db.add(relation)
    db.flush()
    enqueue_concept_event(db, source)
    db.commit()
    db.refresh(relation)
    return relation


@router.delete(
    "/concept-relations/{relation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_concept_relation(
    relation_id: int,
    db: DatabaseSession,
    profile: CurrentProfile,
) -> Response:
    relation = db.scalar(
        select(ConceptRelation)
        .join(Concept, Concept.id == ConceptRelation.source_concept_id)
        .options(selectinload(ConceptRelation.source_concept))
        .where(
            ConceptRelation.id == relation_id,
            Concept.profile_id == profile.id,
        )
    )
    if relation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Concept relation not found",
        )
    source = relation.source_concept
    source.outgoing_relations.remove(relation)
    db.flush()
    enqueue_concept_event(db, source)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
