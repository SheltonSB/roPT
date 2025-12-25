"""
planning/router.py
Planning endpoints to manage the base graph and trigger routes.
"""

from __future__ import annotations

from typing import Dict, Any

from fastapi import APIRouter, Depends

from .graph_manager import GraphManager
from ..cuopt_client import client as cuopt_client
from ..deps import require_dashboard_key


def create_planning_router(graph_manager: GraphManager) -> APIRouter:
    router = APIRouter(prefix="/planning", tags=["planning"])

    @router.get("/graph")
    async def get_graph():
        return {"graph": graph_manager.build_weighted_graph()}

    @router.put("/graph")
    async def put_graph(graph: Dict[str, Any], _auth: None = Depends(require_dashboard_key)):
        await graph_manager.save_base_graph(graph)
        return {"ok": True}

    @router.post("/route")
    async def plan_route(constraints: Dict[str, Any] | None = None):
        matrix_data = graph_manager.get_cost_matrix()
        out = cuopt_client.solve(matrix_data=matrix_data, constraints=constraints or {})
        return out

    return router
