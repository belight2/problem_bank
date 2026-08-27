import asyncio
import logging
from contextlib import suppress

from app.core.config import Settings
from app.db.session import SessionLocal
from app.services.fuseki import FusekiClient
from app.services.graph_sync import process_graph_outbox_batch

logger = logging.getLogger(__name__)


async def wait_for_next_cycle(stop_event: asyncio.Event, seconds: float) -> None:
    with suppress(TimeoutError):
        await asyncio.wait_for(stop_event.wait(), timeout=seconds)


async def run_graph_sync_worker(stop_event: asyncio.Event, settings: Settings) -> None:
    client = FusekiClient(
        settings.fuseki_base_url,
        settings.fuseki_dataset,
        timeout_seconds=settings.fuseki_request_timeout_seconds,
    )
    logger.info("Fuseki Outbox 동기화 작업자를 시작합니다.")
    while not stop_event.is_set():
        try:
            result = await asyncio.to_thread(
                process_graph_outbox_batch,
                SessionLocal,
                client,
                batch_size=settings.graph_sync_batch_size,
                max_attempts=settings.graph_sync_max_attempts,
                lock_timeout_seconds=settings.graph_sync_lock_timeout_seconds,
            )
            if result.claimed:
                logger.info(
                    "그래프 이벤트 처리: claimed=%d completed=%d retried=%d failed=%d",
                    result.claimed,
                    result.completed,
                    result.retried,
                    result.failed,
                )
        except Exception:
            logger.exception("그래프 Outbox 처리 주기에 실패했습니다.")
        await wait_for_next_cycle(stop_event, settings.graph_sync_poll_seconds)
    logger.info("Fuseki Outbox 동기화 작업자를 종료합니다.")
