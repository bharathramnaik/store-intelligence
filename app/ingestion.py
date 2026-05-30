from __future__ import annotations

from typing import Any
from pydantic import ValidationError

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EventIngest, IngestResponse
from app.db.base import EventModel, SessionModel
from app.db.session import get_db
from app.core.logging import logger

router = APIRouter(prefix="/events", tags=["events"])


MAX_BATCH_SIZE = 500


@router.post("/ingest", response_model=IngestResponse)
async def ingest_events(
    request: Request,
    payload: list[dict[str, Any]],
    db: AsyncSession = Depends(get_db),
) -> IngestResponse:
    request.state.event_count = len(payload)
    if len(payload) > MAX_BATCH_SIZE:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=422,
            detail=f"Batch exceeds max size of {MAX_BATCH_SIZE}",
        )
    ingested = 0
    failed = 0
    errors: list[dict[str, Any]] = []

    for index, raw_event in enumerate(payload):
        try:
            evt = EventIngest.model_validate(raw_event)
        except ValidationError as exc:
            failed += 1
            errors.append({"index": index, "reason": exc.errors()})
            continue

        try:
            # Upsert event (idempotent by event_id)
            stmt = pg_insert(EventModel).values(
                event_id=evt.event_id,
                store_id=evt.store_id,
                camera_id=evt.camera_id,
                visitor_id=evt.visitor_id,
                event_type=evt.event_type,
                timestamp=evt.timestamp,
                zone_id=evt.zone_id,
                dwell_ms=evt.dwell_ms,
                is_staff=evt.is_staff,
                confidence=evt.confidence,
                metadata_json=evt.metadata.model_dump(),
            ).on_conflict_do_nothing(
                index_elements=["event_id"]
            ).returning(EventModel.event_id)
            inserted_event_id = (await db.execute(stmt)).scalar_one_or_none()
            if inserted_event_id is None:
                continue

            # Upsert session on ENTRY / REENTRY / EXIT
            if evt.event_type in ("ENTRY", "REENTRY"):
                sess_stmt = pg_insert(SessionModel).values(
                    visitor_id=evt.visitor_id,
                    store_id=evt.store_id,
                    start_time=evt.timestamp,
                    is_staff=evt.is_staff,
                ).on_conflict_do_nothing(index_elements=["visitor_id"])
                await db.execute(sess_stmt)
            elif evt.event_type == "EXIT":
                from sqlalchemy import text
                await db.execute(
                    text("UPDATE sessions SET end_time = :ts WHERE visitor_id = :vid AND end_time IS NULL"),
                    {"ts": evt.timestamp, "vid": evt.visitor_id},
                )
            ingested += 1
        except Exception as exc:
            failed += 1
            errors.append({"event_id": evt.event_id, "reason": str(exc)})
            logger.warning("event_ingest_failed", event_id=evt.event_id, error=str(exc))

    await db.commit()
    return IngestResponse(ingested=ingested, failed=failed, errors=errors)
