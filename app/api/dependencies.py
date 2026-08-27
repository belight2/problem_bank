from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.profile import Profile
from app.services.fuseki import FusekiClient

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


def get_fuseki_client() -> FusekiClient:
    settings = get_settings()
    return FusekiClient(
        settings.fuseki_base_url,
        settings.fuseki_dataset,
        timeout_seconds=settings.fuseki_request_timeout_seconds,
    )


FusekiConnection = Annotated[FusekiClient, Depends(get_fuseki_client)]
