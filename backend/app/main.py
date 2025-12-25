"""
main.py
Unified backend entrypoint. Creates the FastAPI app and wires everything.
"""

from __future__ import annotations

import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .runtime_state import RuntimeState, now_ms
from .schemas import SafetyEventIn
from .db.mongo import ensure_indexes, get_db
from .repos import events_repo
from .routers import health, zones, events, runs, metrics
from .ws import ConnectionManager


def create_app() -> FastAPI:
    app = FastAPI(title="ROPT Backend", version="1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    state = RuntimeState(max_events=settings.max_events)
    queue: "asyncio.Queue[SafetyEventIn]" = asyncio.Queue(
        maxsize=settings.event_queue_max
    )
    ws_manager = ConnectionManager()

    # include routers
    app.include_router(health.router)
    app.include_router(zones.router)
    app.include_router(events.router)
    app.include_router(runs.router)
    app.include_router(metrics.router)

    # bind shared state into routers that need it
    events.bind(state, queue)
    runs.bind_state(state)

    @app.on_event("startup")
    async def startup():
        await get_db().command("ping")
        await ensure_indexes()
        asyncio.create_task(_event_processor(state, queue, ws_manager))

    @app.get("/state")
    async def get_state():
        return state.snapshot()

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await ws_manager.connect(ws)
        try:
            await ws.send_json({"type": "snapshot", "data": state.snapshot()})
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            ws_manager.disconnect(ws)

    return app


async def _event_processor(
    state: RuntimeState,
    queue: "asyncio.Queue[SafetyEventIn]",
    ws_manager: ConnectionManager,
) -> None:
    while True:
        e = await queue.get()
        try:
            run_id = e.run_id or state.active_run_id

            actor = state.upsert_actor(e.actor_id, e.ts_ms)
            prev = actor.zones.get(e.zone_id, False)
            inside = True if "ENTER" in e.event_type else False if "EXIT" in e.event_type else prev
            actor.zones[e.zone_id] = inside

            doc = e.model_dump()
            doc["run_id"] = run_id
            doc["received_ms"] = now_ms()
            _id = await events_repo.insert_event(doc)
            doc["_id"] = _id

            state.push_event(doc)
            await ws_manager.broadcast_json({"type": "snapshot", "data": state.snapshot()})
        finally:
            queue.task_done()


app = create_app()

__all__ = ["app", "create_app"]
