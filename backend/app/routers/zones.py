"""
zones.py
Stores and retrieves zone polygons in MongoDB.
"""

from fastapi import APIRouter

from ..schemas import ZonesPayload
from ..repos import zones_repo
from ..planning.graph_manager import GraphManager
from ..planning.spatial_manager import SpatialManager

router = APIRouter()
_graph_manager: GraphManager | None = None
_spatial_manager: SpatialManager | None = None


def bind_graph(manager: GraphManager):
    global _graph_manager
    _graph_manager = manager


def bind_spatial(manager: SpatialManager):
    global _spatial_manager
    _spatial_manager = manager


@router.get("/zones")
async def get_zones():
    return {"zones": await zones_repo.get_zones()}


@router.put("/zones")
async def put_zones(payload: ZonesPayload):
    zones = [z.model_dump() for z in payload.zones]
    out = await zones_repo.upsert_zones(zones)
    if _graph_manager is not None:
        _graph_manager.refresh_zone_index(zones)
    if _spatial_manager is not None:
        await _spatial_manager.recompute_mappings()
        if _graph_manager is not None:
            _graph_manager.zone_to_nodes = _spatial_manager.zone_to_nodes
            _graph_manager._recompute_blocked_nodes()
    return out
