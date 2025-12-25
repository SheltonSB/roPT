"""
runtime_state.py
In-memory view of actors/zones and recent events so the API can respond quickly.
MongoDB handles durable history; this keeps the live snapshot.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List
import time
import json

import redis.asyncio as redis


def now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class ActorState:
    last_seen_ms: int
    zones: Dict[str, bool]


class RuntimeState:
    def __init__(self, max_events: int = 5000):
        self.actors: Dict[str, ActorState] = {}
        self.events: List[dict] = []
        self.max_events = max_events

        # Active run for tagging events if edge doesn't provide run_id
        self.active_run_id: str | None = None

    async def upsert_actor(self, actor_id: str, ts_ms: int) -> ActorState:
        st = self.actors.get(actor_id)
        if st is None:
            st = ActorState(last_seen_ms=ts_ms, zones={})
            self.actors[actor_id] = st
        st.last_seen_ms = ts_ms
        return st

    async def push_event(self, evt: dict) -> None:
        self.events.append(evt)
        if len(self.events) > self.max_events:
            del self.events[: len(self.events) - self.max_events]

    async def save_actor(self, actor_id: str, actor: ActorState) -> None:
        self.actors[actor_id] = actor

    async def snapshot(self) -> dict:
        return {
            "ts_ms": now_ms(),
            "active_run_id": self.active_run_id,
            "actors": {aid: asdict(st) for aid, st in self.actors.items()},
            "recent_events": self.events[-100:],
        }

    async def get_active_run_id(self) -> str | None:
        return self.active_run_id

    async def set_active_run_id(self, run_id: str | None) -> None:
        self.active_run_id = run_id


class RedisRuntimeState:
    def __init__(self, client: "redis.Redis", max_events: int = 5000):
        self.client = client
        self.max_events = max_events
        self.key_actors = "ropt:actors"
        self.key_events = "ropt:events"
        self.key_active_run = "ropt:active_run_id"

    async def upsert_actor(self, actor_id: str, ts_ms: int) -> ActorState:
        raw = await self.client.hget(self.key_actors, actor_id)
        if raw:
            data = json.loads(raw)
            zones = data.get("zones", {})
        else:
            zones = {}
        st = ActorState(last_seen_ms=ts_ms, zones=zones)
        await self.client.hset(self.key_actors, actor_id, json.dumps(asdict(st)))
        return st

    async def push_event(self, evt: dict) -> None:
        await self.client.lpush(self.key_events, json.dumps(evt))
        await self.client.ltrim(self.key_events, 0, self.max_events - 1)

    async def save_actor(self, actor_id: str, actor: ActorState) -> None:
        await self.client.hset(self.key_actors, actor_id, json.dumps(asdict(actor)))

    async def snapshot(self) -> dict:
        raw_actors = await self.client.hgetall(self.key_actors)
        actors = {}
        for actor_id, raw in raw_actors.items():
            try:
                data = json.loads(raw)
                actors[actor_id] = data
            except Exception:
                continue
        raw_events = await self.client.lrange(self.key_events, 0, 99)
        recent_events = []
        for raw in reversed(raw_events):
            try:
                recent_events.append(json.loads(raw))
            except Exception:
                continue
        active_run_id = await self.client.get(self.key_active_run)
        return {
            "ts_ms": now_ms(),
            "active_run_id": active_run_id,
            "actors": actors,
            "recent_events": recent_events,
        }

    async def get_active_run_id(self) -> str | None:
        return await self.client.get(self.key_active_run)

    async def set_active_run_id(self, run_id: str | None) -> None:
        if run_id is None:
            await self.client.delete(self.key_active_run)
        else:
            await self.client.set(self.key_active_run, run_id)
