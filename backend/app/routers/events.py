"""
events.py
High-throughput event ingestion endpoint.
Writes events to MongoDB and updates live runtime state.
"""

import asyncio
from fastapi import APIRouter

from ..schemas import SafetyEventIn
from ..runtime_state import RuntimeState, now_ms
from ..repos import events_repo

router = APIRouter()
QUEUE: "asyncio.Queue[SafetyEventIn]" = None


def bind(state: RuntimeState, queue: "asyncio.Queue[SafetyEventIn]"):
    router.state_ref = state
    global QUEUE
    QUEUE = queue


@router.post("/events")
async def ingest_event(e: SafetyEventIn):
    try:
        QUEUE.put_nowait(e)
        return {"ok": True}
    except asyncio.QueueFull:
        return {"ok": False, "error": "event_queue_full"}


@router.get("/events")
async def get_events(run_id: str | None = None, since_ms: int | None = None, limit: int = 200):
    return {"events": await events_repo.query_events(run_id=run_id, since_ms=since_ms, limit=limit)}
