"""
spatial_manager.py
Maps graph nodes to zones using polygon containment checks.
"""

from __future__ import annotations

from typing import Dict, List

from shapely.geometry import Point, Polygon

from ..db.mongo import col_graph, col_zones


class SpatialManager:
    def __init__(self):
        self.node_zone_map: Dict[str, List[str]] = {}
        self.zone_to_nodes: Dict[str, List[str]] = {}

    async def recompute_mappings(self) -> None:
        nodes = await col_graph().find({"type": "node"}).to_list(length=None)
        zones = await col_zones().find({}).to_list(length=None)

        node_zone_map: Dict[str, List[str]] = {}
        zone_to_nodes: Dict[str, List[str]] = {}
        for z in zones:
            zone_id = z.get("zone_id")
            poly = z.get("polygon") or []
            if not zone_id or len(poly) < 3:
                continue
            polygon = Polygon(poly)
            for n in nodes:
                node_id = n.get("id")
                x = n.get("x")
                y = n.get("y")
                if node_id is None or x is None or y is None:
                    continue
                if polygon.contains(Point(x, y)):
                    node_zone_map.setdefault(node_id, []).append(zone_id)
                    zone_to_nodes.setdefault(zone_id, []).append(node_id)

        self.node_zone_map = node_zone_map
        self.zone_to_nodes = zone_to_nodes
