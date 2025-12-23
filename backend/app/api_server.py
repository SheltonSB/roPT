from __future__ import annotations

import time
from typing import Dict, Any, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="ROPT Backend", version="0.2.0")

# -------- Models --------
class EventIn(BaseModel):
    ts_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
    event_type: str                # "ZONE_OBSERVATION" | "HUMAN_ENTERED_ZONE" etc.
    actor_id: str                  # "person_3", "robot_1"
    zone_id: Optional[str] = None  # "zone_A"
    payload: Dict[str, Any] = Field(default_factory=dict)

class ActorState(BaseModel):
    actor_id: str
    last_seen_ms: int
    current_zone: Optional[str] = None
    last_event_type: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)

STATE: Dict[str, Any] = {
    "started_ms": int(time.time() * 1000),
    "last_event": None,
    "actors": {},  # actor_id -> ActorState dict
}

# -------- Health + Debug --------
@app.get("/health")
def health():
    return {"ok": True, "service": "ropt-backend"}

@app.get("/state")
def get_state():
    return STATE

@app.get("/actors")
def list_actors():
    return {"actors": list(STATE["actors"].values())}

# -------- Core ingest --------
def _upsert_actor(evt: EventIn) -> ActorState:
    actors: Dict[str, Any] = STATE["actors"]

    existing = actors.get(evt.actor_id)
    if existing:
        actor = ActorState(**existing)
    else:
        actor = ActorState(actor_id=evt.actor_id, last_seen_ms=evt.ts_ms)

    actor.last_seen_ms = evt.ts_ms
    actor.payload = evt.payload or actor.payload
    actor.last_event_type = evt.event_type

    # zone transition detection
    new_zone = evt.zone_id
    old_zone = actor.current_zone

    transition: Optional[str] = None
    if new_zone != old_zone:
        actor.current_zone = new_zone
        if old_zone is None and new_zone is not None:
            transition = "ENTER"
        elif old_zone is not None and new_zone is None:
            transition = "EXIT"
        else:
            transition = "MOVE"  # zone A -> zone B

    actors[evt.actor_id] = actor.model_dump()
    return actor, transition, old_zone, new_zone

@app.post("/events")
def ingest_event(evt: EventIn):
    STATE["last_event"] = evt.model_dump()

    actor, transition, old_zone, new_zone = _upsert_actor(evt)

    # Return transition info so edge can see it’s working
    return {
        "ok": True,
        "actor_id": actor.actor_id,
        "transition": transition,
        "old_zone": old_zone,
        "new_zone": new_zone,
    }
