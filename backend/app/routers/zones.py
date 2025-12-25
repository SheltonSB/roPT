"""
zones.py
Stores and retrieves zone polygons in MongoDB.
"""

from fastapi import APIRouter, Depends

from ..schemas import ZonesPayload
from ..repos import zones_repo
from ..planning.graph_manager import GraphManager
from ..planning.spatial_manager import SpatialManager
from ..deps import get_graph_manager, get_spatial_manager

router = APIRouter()


@router.get("/zones")
async def get_zones():
    return {"zones": await zones_repo.get_zones()}


@router.put("/zones")
async def put_zones(
    payload: ZonesPayload,
    graph_manager: GraphManager = Depends(get_graph_manager),
    spatial_manager: SpatialManager = Depends(get_spatial_manager),
):
    zones = [z.model_dump() for z in payload.zones]
    out = await zones_repo.upsert_zones(zones)
    graph_manager.refresh_zone_index(zones)
    await spatial_manager.recompute_mappings()
    graph_manager.zone_to_nodes = spatial_manager.zone_to_nodes
    graph_manager._recompute_blocked_nodes()
    return out
