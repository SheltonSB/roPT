"""
runs_repo.py
What this file does:
- Manages 'runs' for replay: start/stop sessions and tag events/metrics with run_id.
"""

from __future__ import annotations
from typing import Optional, Dict, Any
from ..db.mongo import col_runs
from ..runtime_state import now_ms


async def start_run(notes: Optional[str] = None) -> str:
    doc = {
        "started_at_ms": now_ms(),
        "ended_at_ms": None,
        "notes": notes,
    }
    r = await col_runs().insert_one(doc)
    return str(r.inserted_id)


async def stop_run(run_id: str, notes: Optional[str] = None) -> Dict[str, Any]:
    from bson import ObjectId
    upd = {"ended_at_ms": now_ms()}
    if notes is not None:
        upd["notes"] = notes
    await col_runs().update_one({"_id": ObjectId(run_id)}, {"$set": upd})
    return {"ok": True, "run_id": run_id}


async def list_runs(limit: int = 50):
    cur = col_runs().find({}, sort=[("started_at_ms", -1)]).limit(limit)
    out = []
    async for d in cur:
        d["_id"] = str(d["_id"])
        out.append(d)
    return out
