"""
@author Shelton Bumhe 
metrics_repo.py
What this file does:
- Stores performance metrics for NVIDIA-style proof (FPS, latency, solve time).
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from ..db.mongo import col_metrics


async def insert_metric(m: Dict[str, Any]) -> str:
    r = await col_metrics().insert_one(m)
    return str(r.inserted_id)


async def query_metrics(run_id: Optional[str] = None, limit: int = 500) -> List[dict]:
    q: Dict[str, Any] = {}
    if run_id:
        q["run_id"] = run_id
    cur = col_metrics().find(q, sort=[("ts_ms", 1)]).limit(limit)
    out = []
    async for d in cur:
        d["_id"] = str(d["_id"])
        out.append(d)
    return out
