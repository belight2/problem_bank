from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import DatabaseSession
from app.api.routes.cards import get_card_or_404
from app.models.note import Note
from app.models.topic import Topic
from app.schemas.note import NoteCreate, NoteRead, NoteUpdate

router = APIRouter(prefix="/cards/{card_id}/notes", tags=["notes"])


def get_note_or_404(card_id: int, note_id: int, db: Session) -> Note:
    note = db.scalar(
        select(Note)
        .options(selectinload(Note.topic))
        .where(Note.id == note_id, Note.card_id == card_id)
    )
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


def get_optional_topic(card_id: int, topic_id: int | None, db: Session) -> Topic | None:
    if topic_id is None:
        return None
    topic = db.scalar(select(Topic).where(Topic.id == topic_id, Topic.card_id == card_id))
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
    return topic


@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
def create_note(card_id: int, payload: NoteCreate, db: DatabaseSession) -> Note:
    get_card_or_404(card_id, db)
    topic = get_optional_topic(card_id, payload.topic_id, db)
    note = Note(
        card_id=card_id,
        topic=topic,
        title=payload.title,
        content_markdown=payload.content_markdown,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("", response_model=list[NoteRead])
def list_notes(
    card_id: int,
    db: DatabaseSession,
    topic_id: Annotated[int | None, Query(gt=0)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[Note]:
    get_card_or_404(card_id, db)
    statement = select(Note).options(selectinload(Note.topic)).where(Note.card_id == card_id)
    if topic_id is not None:
        statement = statement.where(Note.topic_id == topic_id)
    statement = (
        statement.order_by(Note.updated_at.desc(), Note.id.desc()).offset(offset).limit(limit)
    )
    return list(db.scalars(statement).all())


@router.get("/{note_id}", response_model=NoteRead)
def get_note(card_id: int, note_id: int, db: DatabaseSession) -> Note:
    return get_note_or_404(card_id, note_id, db)


@router.patch("/{note_id}", response_model=NoteRead)
def update_note(
    card_id: int,
    note_id: int,
    payload: NoteUpdate,
    db: DatabaseSession,
) -> Note:
    note = get_note_or_404(card_id, note_id, db)
    changes = payload.model_dump(exclude_unset=True)
    if "topic_id" in changes:
        note.topic = get_optional_topic(card_id, changes.pop("topic_id"), db)
    for field, value in changes.items():
        setattr(note, field, value)
    db.commit()
    db.refresh(note)
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(card_id: int, note_id: int, db: DatabaseSession) -> Response:
    note = get_note_or_404(card_id, note_id, db)
    db.delete(note)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
