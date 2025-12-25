"""
events.py
High-throughput event ingestion endpoint.
Writes events to MongoDB and updates live runtime state.
"""

import asyncio
from fastapi import APIRouter, Depends

from ..schemas import SafetyEventIn
from ..repos import events_repo
from ..deps import get_queue, require_edge_key

router = APIRouter()


@router.post("/events")
async def ingest_event(
    e: SafetyEventIn,
    queue: "asyncio.Queue[SafetyEventIn]" = Depends(get_queue),
    _auth: None = Depends(require_edge_key),
):
    try:
        queue.put_nowait(e)
        return {"ok": True}
    except asyncio.QueueFull:
        return {"ok": False, "error": "event_queue_full"}


@router.get("/events")
async def get_events(run_id: str | None = None, since_ms: int | None = None, limit: int = 200):
    return {"events": await events_repo.query_events(run_id=run_id, since_ms=since_ms, limit=limit)}
