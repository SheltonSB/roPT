"""
zones_repo.py
@Shelton Bumhe
- Stores zones as JSON polygons in Mongo.
- Supports live editing via API.
"""

from __future__ import annotations
from typing import List, Dict, Any
from ..db.mongo import col_zones


async def upsert_zones(zones: List[dict]) -> Dict[str, Any]:
    for z in zones:
        await col_zones().update_one(
            {"zone_id": z["zone_id"]},
            {"$set": z},
            upsert=True
        )
    return {"ok": True, "count": len(zones)}


async def get_zones() -> List[dict]:
    cur = col_zones().find({}, sort=[("zone_id", 1)])
    out = []
    async for d in cur:
        d["_id"] = str(d["_id"])
        out.append(d)
    return out
