"""
@author: Shelton Bumhe
runtime_state.py
What this file does:
- Maintains fast, in-memory “live state” for the UI (who is inside which zone right now).
- MongoDB stores the durable log (replay/audit). Memory stores the present.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List
import time


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

    def upsert_actor(self, actor_id: str, ts_ms: int) -> ActorState:
        st = self.actors.get(actor_id)
        if st is None:
            st = ActorState(last_seen_ms=ts_ms, zones={})
            self.actors[actor_id] = st
        st.last_seen_ms = ts_ms
        return st

    def push_event(self, evt: dict) -> None:
        self.events.append(evt)
        if len(self.events) > self.max_events:
            del self.events[: len(self.events) - self.max_events]

    def snapshot(self) -> dict:
        return {
            "ts_ms": now_ms(),
            "active_run_id": self.active_run_id,
            "actors": {aid: asdict(st) for aid, st in self.actors.items()},
            "recent_events": self.events[-100:],
        }
