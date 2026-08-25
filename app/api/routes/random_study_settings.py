from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.dependencies import DatabaseSession
from app.api.routes.cards import get_card_or_404
from app.models.random_study_setting import RandomStudySetting
from app.models.topic import Topic
from app.schemas.random_study_setting import (
    RandomStudySettingRead,
    RandomStudySettingUpdate,
)

router = APIRouter(
    prefix="/cards/{card_id}/random-study-settings",
    tags=["random-study-settings"],
)


@router.get("", response_model=RandomStudySettingRead | None)
def get_random_study_settings(
    card_id: int,
    db: DatabaseSession,
) -> RandomStudySetting | None:
    get_card_or_404(card_id, db)
    return db.get(RandomStudySetting, card_id)


@router.put("", response_model=RandomStudySettingRead)
def save_random_study_settings(
    card_id: int,
    payload: RandomStudySettingUpdate,
    db: DatabaseSession,
) -> RandomStudySetting:
    get_card_or_404(card_id, db)
    if payload.topic_id is not None:
        topic_id = db.scalar(
            select(Topic.id).where(
                Topic.id == payload.topic_id,
                Topic.card_id == card_id,
            )
        )
        if topic_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Topic not found",
            )

    setting = db.get(RandomStudySetting, card_id)
    if setting is None:
        setting = RandomStudySetting(card_id=card_id, **payload.model_dump())
        db.add(setting)
    else:
        setting.problem_count = payload.problem_count
        setting.topic_id = payload.topic_id

    db.commit()
    db.refresh(setting)
    return setting
