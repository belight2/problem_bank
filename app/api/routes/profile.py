from fastapi import APIRouter

from app.api.dependencies import CurrentProfile, DatabaseSession
from app.models.profile import Profile
from app.schemas.profile import ProfileRead, ProfileWrite

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileRead)
def get_profile(profile: CurrentProfile) -> Profile:
    return profile


@router.put("", response_model=ProfileRead)
def update_profile(
    payload: ProfileWrite,
    profile: CurrentProfile,
    db: DatabaseSession,
) -> Profile:
    profile.display_name = payload.display_name
    profile.timezone = payload.timezone
    profile.daily_goal = payload.daily_goal
    profile.is_configured = True
    db.commit()
    db.refresh(profile)
    return profile
