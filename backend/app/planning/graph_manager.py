"""
graph_manager.py
In-memory graph + zone mapping for local planning updates.
"""

from __future__ import annotations

from typing import Dict, List, Any, Set

from shapely.geometry import Point, Polygon

from ..db.mongo import get_db, col_graph


class GraphManager:
    def __init__(self):
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []
        self.zone_to_nodes: Dict[str, List[str]] = {}
        self.blocked_zones: Set[str] = set()
        self.blocked_nodes: Set[str] = set()

    async def load_base_graph(self) -> None:
        doc = await get_db()["map_graph"].find_one({"_id": "base"})
        if doc:
            self.set_base_graph(doc.get("graph", {}))
            return
        # Fallback: rebuild graph from col_graph if present.
        nodes = await col_graph().find({"type": "node"}).to_list(length=None)
        edges = await col_graph().find({"type": "edge"}).to_list(length=None)
        if nodes or edges:
            self.set_base_graph({"nodes": nodes, "edges": edges})

    async def save_base_graph(self, graph: Dict[str, Any]) -> None:
        await get_db()["map_graph"].update_one(
            {"_id": "base"}, {"$set": {"graph": graph}}, upsert=True
        )
        # Persist nodes/edges for spatial mapping
        await col_graph().delete_many({})
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        if nodes:
            await col_graph().insert_many([{**n, "type": "node"} for n in nodes])
        if edges:
            await col_graph().insert_many([{**e, "type": "edge"} for e in edges])
        self.set_base_graph(graph)

    def set_base_graph(self, graph: Dict[str, Any]) -> None:
        nodes = graph.get("nodes", [])
        self.nodes = {n["id"]: n for n in nodes if "id" in n}
        self.edges = graph.get("edges", [])
        # Recompute zone mapping if zones already present.
        if self.zone_to_nodes:
            self._recompute_blocked_nodes()

    def refresh_zone_index(self, zones: List[Dict[str, Any]]) -> None:
        zone_to_nodes: Dict[str, List[str]] = {}
        for z in zones:
            zone_id = z.get("zone_id")
            polygon = z.get("polygon") or []
            if not zone_id or not polygon:
                continue
            nodes_in_zone = []
            polygon_obj = Polygon(polygon)
            for node_id, node in self.nodes.items():
                x = node.get("x")
                y = node.get("y")
                if x is None or y is None:
                    continue
                if polygon_obj.contains(Point(x, y)):
                    nodes_in_zone.append(node_id)
            zone_to_nodes[zone_id] = nodes_in_zone
        self.zone_to_nodes = zone_to_nodes
        self._recompute_blocked_nodes()

    def update_zone_block(self, zone_id: str, blocked: bool) -> None:
        if blocked:
            self.blocked_zones.add(zone_id)
        else:
            self.blocked_zones.discard(zone_id)
        self._recompute_blocked_nodes()

    def _recompute_blocked_nodes(self) -> None:
        blocked_nodes: Set[str] = set()
        for zone_id in self.blocked_zones:
            blocked_nodes.update(self.zone_to_nodes.get(zone_id, []))
        self.blocked_nodes = blocked_nodes

    def build_weighted_graph(self) -> Dict[str, Any]:
        weighted_edges = []
        for e in self.edges:
            src = e.get("from")
            dst = e.get("to")
            weight = e.get("weight", 1.0)
            if src in self.blocked_nodes or dst in self.blocked_nodes:
                weight = float("inf")
            weighted_edges.append({**e, "weight": weight})
        return {
            "nodes": list(self.nodes.values()),
            "edges": weighted_edges,
            "blocked_nodes": list(self.blocked_nodes),
        }

    def get_cost_matrix(self) -> Dict[str, Any]:
        """
        Build a cost matrix for the VRP solver with blocked nodes penalized.
        """
        nodes = list(self.nodes.values())
        node_id_to_idx = {n["id"]: i for i, n in enumerate(nodes) if "id" in n}
        n_count = len(nodes)
        inf = 1_000_000.0
        matrix = [[inf] * n_count for _ in range(n_count)]
        for i in range(n_count):
            matrix[i][i] = 0.0

        for e in self.edges:
            src = e.get("from")
            dst = e.get("to")
            weight = e.get("weight", 1.0)
            if src in self.blocked_nodes or dst in self.blocked_nodes:
                weight = inf
            if src in node_id_to_idx and dst in node_id_to_idx:
                u = node_id_to_idx[src]
                v = node_id_to_idx[dst]
                matrix[u][v] = weight

        return {
            "matrix": matrix,
            "node_map": node_id_to_idx,
            "nodes": nodes,
        }
