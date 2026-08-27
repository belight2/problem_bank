from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import LOCAL_PROFILE_ID, CurrentProfile, DatabaseSession
from app.models.card import Card
from app.models.graph_outbox import GraphOutboxEventType
from app.schemas.card import CardCreate, CardRead, CardUpdate
from app.services.graph_outbox import enqueue_card_event

router = APIRouter(prefix="/cards", tags=["cards"])


def get_card_or_404(
    card_id: int,
    db: Session,
    profile_id: int = LOCAL_PROFILE_ID,
) -> Card:
    card = db.scalar(select(Card).where(Card.id == card_id, Card.profile_id == profile_id))
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    return card


@router.post("", response_model=CardRead, status_code=status.HTTP_201_CREATED)
def create_card(
    payload: CardCreate,
    db: DatabaseSession,
    profile: CurrentProfile,
) -> Card:
    card = Card(profile=profile, **payload.model_dump())
    db.add(card)
    db.flush()
    enqueue_card_event(db, card)
    db.commit()
    db.refresh(card)
    return card


@router.get("", response_model=list[CardRead])
def list_cards(
    db: DatabaseSession,
    profile: CurrentProfile,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[Card]:
    statement = (
        select(Card)
        .where(Card.profile_id == profile.id)
        .order_by(Card.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


@router.get("/{card_id}", response_model=CardRead)
def get_card(card_id: int, db: DatabaseSession, profile: CurrentProfile) -> Card:
    return get_card_or_404(card_id, db, profile.id)


@router.patch("/{card_id}", response_model=CardRead)
def update_card(
    card_id: int,
    payload: CardUpdate,
    db: DatabaseSession,
    profile: CurrentProfile,
) -> Card:
    card = get_card_or_404(card_id, db, profile.id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(card, field, value)

    enqueue_card_event(db, card)
    db.commit()
    db.refresh(card)
    return card


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(
    card_id: int,
    db: DatabaseSession,
    profile: CurrentProfile,
) -> Response:
    card = get_card_or_404(card_id, db, profile.id)
    enqueue_card_event(db, card, GraphOutboxEventType.DELETE)
    db.delete(card)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
