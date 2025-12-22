"""
events_repo.py
@Shelton Bumhe
- Writes safety events to MongoDB (durable log).
- Supports queries for replay and dashboards.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from ..db.mongo import col_events


async def insert_event(evt: Dict[str, Any]) -> str:
    r = await col_events().insert_one(evt)
    return str(r.inserted_id)


async def query_events(
    run_id: Optional[str] = None,
    since_ms: Optional[int] = None,
    limit: int = 200
) -> List[dict]:
    q: Dict[str, Any] = {}
    if run_id:
        q["run_id"] = run_id
    if since_ms is not None:
        q["ts_ms"] = {"$gte": since_ms}

    cur = col_events().find(q, sort=[("ts_ms", 1)]).limit(limit)
    out = []
    async for d in cur:
        d["_id"] = str(d["_id"])
        out.append(d)
    return out
