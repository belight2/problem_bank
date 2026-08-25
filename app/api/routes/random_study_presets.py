from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import DatabaseSession
from app.api.routes.cards import get_card_or_404
from app.models.random_study_preset import RandomStudyPreset
from app.models.random_study_setting import RandomStudySetting
from app.models.topic import Topic
from app.schemas.random_study_preset import RandomStudyPresetRead, RandomStudyPresetWrite

router = APIRouter(
    prefix="/cards/{card_id}/random-study-presets",
    tags=["random-study-presets"],
)


def get_preset_or_404(card_id: int, preset_id: int, db: Session) -> RandomStudyPreset:
    preset = db.scalar(
        select(RandomStudyPreset).where(
            RandomStudyPreset.id == preset_id,
            RandomStudyPreset.card_id == card_id,
        )
    )
    if preset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Random study preset not found",
        )
    return preset


def validate_topic(card_id: int, topic_id: int | None, db: Session) -> None:
    if topic_id is None:
        return
    existing_topic_id = db.scalar(
        select(Topic.id).where(
            Topic.id == topic_id,
            Topic.card_id == card_id,
        )
    )
    if existing_topic_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found",
        )


def commit_preset_change(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Random study preset name already exists",
        ) from error


@router.get("", response_model=list[RandomStudyPresetRead])
def list_random_study_presets(
    card_id: int,
    db: DatabaseSession,
) -> list[RandomStudyPreset]:
    get_card_or_404(card_id, db)
    statement = (
        select(RandomStudyPreset)
        .where(RandomStudyPreset.card_id == card_id)
        .order_by(RandomStudyPreset.id.asc())
    )
    return list(db.scalars(statement).all())


@router.post("", response_model=RandomStudyPresetRead, status_code=status.HTTP_201_CREATED)
def create_random_study_preset(
    card_id: int,
    payload: RandomStudyPresetWrite,
    db: DatabaseSession,
) -> RandomStudyPreset:
    get_card_or_404(card_id, db)
    validate_topic(card_id, payload.topic_id, db)
    preset = RandomStudyPreset(card_id=card_id, **payload.model_dump())
    db.add(preset)
    commit_preset_change(db)
    db.refresh(preset)
    return preset


@router.put("/{preset_id}", response_model=RandomStudyPresetRead)
def update_random_study_preset(
    card_id: int,
    preset_id: int,
    payload: RandomStudyPresetWrite,
    db: DatabaseSession,
) -> RandomStudyPreset:
    preset = get_preset_or_404(card_id, preset_id, db)
    validate_topic(card_id, payload.topic_id, db)
    for field, value in payload.model_dump().items():
        setattr(preset, field, value)

    setting = db.get(RandomStudySetting, card_id)
    if setting is not None and setting.preset_id == preset.id:
        setting.topic_id = preset.topic_id
        setting.problem_count = preset.problem_count

    commit_preset_change(db)
    db.refresh(preset)
    return preset


@router.delete("/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_random_study_preset(
    card_id: int,
    preset_id: int,
    db: DatabaseSession,
) -> Response:
    preset = get_preset_or_404(card_id, preset_id, db)
    db.delete(preset)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
