"""
api_server.py
What this file does:
- Wires everything together:
  - MongoDB connection + indexes
  - Async event queue
  - Background processor that:
      1) updates live state
      2) writes event to MongoDB
- Exposes routes for zones/events/runs/metrics
"""

from __future__ import annotations
import asyncio

from fastapi import FastAPI

from .config import settings
from .runtime_state import RuntimeState, now_ms
from .schemas import SafetyEventIn
from .db.mongo import ensure_indexes, get_db
from .repos import events_repo
from .routers import health, zones, events, runs, metrics

app = FastAPI(title="ROPT Backend", version="1.0")

STATE = RuntimeState(max_events=settings.max_events)
QUEUE: "asyncio.Queue[SafetyEventIn]" = asyncio.Queue(maxsize=settings.event_queue_max)

# include routers
app.include_router(health.router)
app.include_router(zones.router)
app.include_router(events.router)
app.include_router(runs.router)
app.include_router(metrics.router)

# bind shared state into routers that need it
events.bind(STATE, QUEUE)
runs.bind_state(STATE)

@app.on_event("startup")
async def startup():
    # force DB init early (fail fast if Mongo isn't reachable)
    await get_db().command("ping")
    await ensure_indexes()
    asyncio.create_task(_event_processor())

@app.get("/state")
async def state():
    return STATE.snapshot()

async def _event_processor():
    while True:
        e = await QUEUE.get()
        try:
            # attach run_id if edge didn't send it
            run_id = e.run_id or STATE.active_run_id

            # update live state
            actor = STATE.upsert_actor(e.actor_id, e.ts_ms)
            prev = actor.zones.get(e.zone_id, False)
            inside = True if "ENTER" in e.event_type else False if "EXIT" in e.event_type else prev
            actor.zones[e.zone_id] = inside

            # durable event log in MongoDB
            doc = e.model_dump()
            doc["run_id"] = run_id
            doc["received_ms"] = now_ms()
            _id = await events_repo.insert_event(doc)
            doc["_id"] = _id

            # ring buffer for UI
            STATE.push_event(doc)

        finally:
            QUEUE.task_done()
