"""
main.py
Unified backend entrypoint. Creates the FastAPI app and wires everything.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .runtime_state import RuntimeState, now_ms
from .schemas import SafetyEventIn
from .db.mongo import ensure_indexes, get_db
from .repos import events_repo, runs_repo, zones_repo
from .routers import health, zones, events, runs, metrics
from .ws import ConnectionManager
from .planning import GraphManager, SpatialManager, create_planning_router
from .cuopt_client import client as cuopt_client
from .db.mongo import col_actors


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
    graph_manager = GraphManager()
    spatial_manager = SpatialManager()

    # include routers
    app.include_router(health.router)
    app.include_router(zones.router)
    app.include_router(events.router)
    app.include_router(runs.router)
    app.include_router(metrics.router)
    app.include_router(create_planning_router(graph_manager))

    # bind shared state into routers that need it
    events.bind(state, queue)
    runs.bind_state(state)
    zones.bind_graph(graph_manager)
    zones.bind_spatial(spatial_manager)

    @app.on_event("startup")
    async def startup():
        await get_db().command("ping")
        await ensure_indexes()
        await graph_manager.load_base_graph()
        try:
            current_zones = await zones_repo.get_zones()
            graph_manager.refresh_zone_index(current_zones)
            await spatial_manager.recompute_mappings()
            graph_manager.zone_to_nodes = spatial_manager.zone_to_nodes
            graph_manager._recompute_blocked_nodes()
        except Exception:
            # If zones are not available yet, keep empty mapping.
            pass
        await _restore_blocked_state(graph_manager)
        asyncio.create_task(_event_processor(state, queue, ws_manager, graph_manager))

    @app.get("/state")
    async def get_state():
        snap = state.snapshot()
        snap["blocked_zones"] = list(graph_manager.blocked_zones)
        snap["blocked_nodes"] = list(graph_manager.blocked_nodes)
        return snap

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await ws_manager.connect(ws)
        try:
            snap = state.snapshot()
            snap["blocked_zones"] = list(graph_manager.blocked_zones)
            snap["blocked_nodes"] = list(graph_manager.blocked_nodes)
            await ws.send_json({"type": "snapshot", "data": snap})
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            ws_manager.disconnect(ws)

    return app


async def _event_processor(
    state: RuntimeState,
    queue: "asyncio.Queue[SafetyEventIn]",
    ws_manager: ConnectionManager,
    graph_manager: GraphManager,
) -> None:
    while True:
        e = await queue.get()
        try:
            run_id = e.run_id or state.active_run_id
            if run_id is None:
                run_id = await runs_repo.start_run("auto_run")
                state.active_run_id = run_id

            actor = state.upsert_actor(e.actor_id, e.ts_ms)
            prev = actor.zones.get(e.zone_id, False)
            inside = True if "ENTER" in e.event_type else False if "EXIT" in e.event_type else prev
            actor.zones[e.zone_id] = inside

            doc = e.model_dump()
            doc["run_id"] = run_id
            doc["received_ms"] = now_ms()
            try:
                _id = await events_repo.insert_event(doc)
                doc["_id"] = _id
            except Exception as exc:
                logger.exception("Failed to persist event to MongoDB: %s", exc)

            state.push_event(doc)
            snap = state.snapshot()
            snap["blocked_zones"] = list(graph_manager.blocked_zones)
            snap["blocked_nodes"] = list(graph_manager.blocked_nodes)
            await ws_manager.broadcast_json({"type": "snapshot", "data": snap})
            if e.zone_id and ("ENTER" in e.event_type or "EXIT" in e.event_type):
                graph_manager.update_zone_block(
                    e.zone_id, blocked="ENTER" in e.event_type
                )
                graph = graph_manager.build_weighted_graph()
                result = cuopt_client.solve(graph=graph, constraints={})
                await ws_manager.broadcast_json(
                    {
                        "type": "route_update",
                        "data": {
                            "robot_id": result.get("robot_id", "robot_01"),
                            "optimal_path": result.get("route", []),
                            "candidates": result.get("candidates", []),
                            "is_reroute": "ENTER" in e.event_type,
                        },
                    }
                )
            await _persist_actor_state(state, e.actor_id)
        finally:
            queue.task_done()


async def _restore_blocked_state(graph_manager: GraphManager) -> None:
    # Reconstruct blocked zones from persisted actor states.
    cur = col_actors().find({})
    zone_counts: dict[str, int] = {}
    async for actor in cur:
        zones = actor.get("zones") or {}
        for zone_id, inside in zones.items():
            if inside:
                zone_counts[zone_id] = zone_counts.get(zone_id, 0) + 1
    for zone_id, count in zone_counts.items():
        if count > 0:
            graph_manager.update_zone_block(zone_id, blocked=True)


async def _persist_actor_state(state: RuntimeState, actor_id: str) -> None:
    # Save only the actor that changed.
    actor = state.actors.get(actor_id)
    if actor is None:
        return
    await col_actors().update_one(
        {"actor_id": actor_id},
        {"$set": {"actor_id": actor_id, "last_seen_ms": actor.last_seen_ms, "zones": actor.zones}},
        upsert=True,
    )


logger = logging.getLogger("ropt.backend")
app = create_app()

__all__ = ["app", "create_app"]
