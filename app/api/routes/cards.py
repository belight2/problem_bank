from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import DatabaseSession
from app.models.card import Card
from app.schemas.card import CardCreate, CardRead, CardUpdate

router = APIRouter(prefix="/cards", tags=["cards"])


def get_card_or_404(card_id: int, db: Session) -> Card:
    card = db.get(Card, card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    return card


@router.post("", response_model=CardRead, status_code=status.HTTP_201_CREATED)
def create_card(payload: CardCreate, db: DatabaseSession) -> Card:
    card = Card(**payload.model_dump())
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


@router.get("", response_model=list[CardRead])
def list_cards(
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[Card]:
    statement = select(Card).order_by(Card.id.desc()).offset(offset).limit(limit)
    return list(db.scalars(statement).all())


@router.get("/{card_id}", response_model=CardRead)
def get_card(card_id: int, db: DatabaseSession) -> Card:
    return get_card_or_404(card_id, db)


@router.patch("/{card_id}", response_model=CardRead)
def update_card(card_id: int, payload: CardUpdate, db: DatabaseSession) -> Card:
    card = get_card_or_404(card_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(card, field, value)

    db.commit()
    db.refresh(card)
    return card


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(card_id: int, db: DatabaseSession) -> Response:
    card = get_card_or_404(card_id, db)
    db.delete(card)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
