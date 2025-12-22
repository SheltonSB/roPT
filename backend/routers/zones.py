"""
@Shelton Bumhe
zones.py
What this file does:
- Stores/retrieves zone polygons in MongoDB.
"""

from fastapi import APIRouter
from ..schemas import ZonesPayload
from ..repos import zones_repo

router = APIRouter()

@router.get("/zones")
async def get_zones():
    return {"zones": await zones_repo.get_zones()}

@router.put("/zones")
async def put_zones(payload: ZonesPayload):
    zones = [z.model_dump() for z in payload.zones]
    return await zones_repo.upsert_zones(zones)
