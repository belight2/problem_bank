from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.dependencies import DatabaseSession
from app.api.routes.cards import get_card_or_404
from app.models.random_study_preset import RandomStudyPreset
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
    preset = None
    if payload.preset_id is not None:
        preset = db.scalar(
            select(RandomStudyPreset).where(
                RandomStudyPreset.id == payload.preset_id,
                RandomStudyPreset.card_id == card_id,
            )
        )
        if preset is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Random study preset not found",
            )

    topic_id = preset.topic_id if preset is not None else payload.topic_id
    problem_count = preset.problem_count if preset is not None else payload.problem_count
    selection_mode = preset.selection_mode if preset is not None else payload.selection_mode
    incorrect_rate_threshold = (
        preset.incorrect_rate_threshold if preset is not None else payload.incorrect_rate_threshold
    )
    minimum_attempt_count = (
        preset.minimum_attempt_count if preset is not None else payload.minimum_attempt_count
    )
    incorrect_count_threshold = (
        preset.incorrect_count_threshold
        if preset is not None
        else payload.incorrect_count_threshold
    )
    if topic_id is not None:
        topic_id = db.scalar(
            select(Topic.id).where(
                Topic.id == topic_id,
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
        setting = RandomStudySetting(
            card_id=card_id,
            topic_id=topic_id,
            problem_count=problem_count,
            preset_id=preset.id if preset is not None else None,
            selection_mode=selection_mode,
            incorrect_rate_threshold=incorrect_rate_threshold,
            minimum_attempt_count=minimum_attempt_count,
            incorrect_count_threshold=incorrect_count_threshold,
        )
        db.add(setting)
    else:
        setting.problem_count = problem_count
        setting.topic_id = topic_id
        setting.preset_id = preset.id if preset is not None else None
        setting.selection_mode = selection_mode
        setting.incorrect_rate_threshold = incorrect_rate_threshold
        setting.minimum_attempt_count = minimum_attempt_count
        setting.incorrect_count_threshold = incorrect_count_threshold

    db.commit()
    db.refresh(setting)
    return setting
