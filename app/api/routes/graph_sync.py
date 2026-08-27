from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import DatabaseSession
from app.core.config import get_settings
from app.schemas.graph_sync import (
    GraphOutboxEventRead,
    GraphRetryRead,
    GraphSyncStatusRead,
)
from app.services.graph_sync_admin import (
    GraphEventNotRetryableError,
    InvalidGraphEventError,
    get_graph_sync_status,
    list_failed_graph_events,
    retry_failed_graph_event,
)

router = APIRouter(prefix="/graph-sync", tags=["graph-sync"])


@router.get("/status", response_model=GraphSyncStatusRead)
def read_graph_sync_status(db: DatabaseSession) -> GraphSyncStatusRead:
    snapshot = get_graph_sync_status(db)
    return GraphSyncStatusRead(
        worker_enabled=get_settings().graph_sync_enabled,
        **asdict(snapshot),
    )


@router.get("/events/failed", response_model=list[GraphOutboxEventRead])
def read_failed_graph_events(
    db: DatabaseSession,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[GraphOutboxEventRead]:
    return [
        GraphOutboxEventRead.model_validate(event)
        for event in list_failed_graph_events(db, limit=limit)
    ]


@router.post(
    "/events/{event_id}/retry",
    response_model=GraphRetryRead,
    status_code=status.HTTP_201_CREATED,
)
def retry_graph_event(event_id: int, db: DatabaseSession) -> GraphRetryRead:
    try:
        result = retry_failed_graph_event(db, event_id)
    except GraphEventNotRetryableError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except InvalidGraphEventError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="그래프 이벤트를 찾을 수 없습니다.")
    db.commit()
    return GraphRetryRead(
        superseded_event_id=result.superseded_event_id,
        retry_event=GraphOutboxEventRead.model_validate(result.retry_event),
    )
