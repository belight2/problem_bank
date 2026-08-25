from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import DatabaseSession
from app.api.routes.cards import get_card_or_404
from app.models.problem import Problem
from app.models.topic import Topic
from app.schemas.topic import TopicCreate, TopicRead, TopicUpdate

router = APIRouter(prefix="/cards/{card_id}/topics", tags=["topics"])


def get_topic_or_404(card_id: int, topic_id: int, db: Session) -> Topic:
    statement = select(Topic).where(Topic.id == topic_id, Topic.card_id == card_id)
    topic = db.scalar(statement)
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
    return topic


def ensure_topic_name_available(
    card_id: int,
    name: str,
    db: Session,
    *,
    exclude_topic_id: int | None = None,
) -> None:
    statement = select(Topic.id).where(
        Topic.card_id == card_id,
        Topic.name == name,
    )
    if exclude_topic_id is not None:
        statement = statement.where(Topic.id != exclude_topic_id)

    if db.scalar(statement.limit(1)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Topic name already exists",
        )


def commit_topic_name_change(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Topic name already exists",
        ) from error


@router.post("", response_model=TopicRead, status_code=status.HTTP_201_CREATED)
def create_topic(card_id: int, payload: TopicCreate, db: DatabaseSession) -> Topic:
    get_card_or_404(card_id, db)
    ensure_topic_name_available(card_id, payload.name, db)
    topic = Topic(card_id=card_id, **payload.model_dump())
    db.add(topic)
    commit_topic_name_change(db)
    db.refresh(topic)
    return topic


@router.get("", response_model=list[TopicRead])
def list_topics(card_id: int, db: DatabaseSession) -> list[Topic]:
    get_card_or_404(card_id, db)
    statement = select(Topic).where(Topic.card_id == card_id).order_by(Topic.id.asc())
    return list(db.scalars(statement).all())


@router.get("/{topic_id}", response_model=TopicRead)
def get_topic(card_id: int, topic_id: int, db: DatabaseSession) -> Topic:
    return get_topic_or_404(card_id, topic_id, db)


@router.patch("/{topic_id}", response_model=TopicRead)
def update_topic(
    card_id: int,
    topic_id: int,
    payload: TopicUpdate,
    db: DatabaseSession,
) -> Topic:
    topic = get_topic_or_404(card_id, topic_id, db)
    ensure_topic_name_available(card_id, payload.name, db, exclude_topic_id=topic_id)
    topic.name = payload.name
    commit_topic_name_change(db)
    db.refresh(topic)
    return topic


@router.delete("/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_topic(card_id: int, topic_id: int, db: DatabaseSession) -> Response:
    topic = get_topic_or_404(card_id, topic_id, db)
    problem_id = db.scalar(select(Problem.id).where(Problem.topic_id == topic_id).limit(1))
    if problem_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Topic is in use",
        )

    db.delete(topic)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Topic is in use",
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
