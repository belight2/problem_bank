from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GraphSyncStatusRead(BaseModel):
    worker_enabled: bool
    pending_count: int
    processing_count: int
    completed_count: int
    failed_count: int
    superseded_count: int
    oldest_open_created_at: datetime | None
    last_completed_at: datetime | None


class GraphOutboxEventRead(BaseModel):
    id: int
    aggregate_type: str
    aggregate_id: str
    event_type: str
    status: str
    attempt_count: int
    available_at: datetime
    locked_at: datetime | None
    processed_at: datetime | None
    last_error: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GraphRetryRead(BaseModel):
    superseded_event_id: int
    retry_event: GraphOutboxEventRead
