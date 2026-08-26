from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.profile import Profile

DatabaseSession = Annotated[Session, Depends(get_db)]

LOCAL_PROFILE_ID = 1


def get_current_profile(db: DatabaseSession) -> Profile:
    profile = db.get(Profile, LOCAL_PROFILE_ID)
    if profile is None:
        profile = Profile(id=LOCAL_PROFILE_ID)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


CurrentProfile = Annotated[Profile, Depends(get_current_profile)]
