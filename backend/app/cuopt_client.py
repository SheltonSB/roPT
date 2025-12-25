"""
cuopt_client.py
Minimal HTTP client for cuOpt. Provides a stubbed response if cuOpt is absent.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import requests

from .config import settings

logger = logging.getLogger(__name__)


class CuOptClient:
    def __init__(self, base_url: str | None = None, timeout_s: float | None = None):
        self.base_url = base_url or settings.cuopt_base_url
        self.timeout_s = timeout_s or settings.cuopt_timeout_s

    def solve(self, matrix_data: Dict[str, Any], constraints: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a VRP request to cuOpt using a cost matrix. Falls back if unavailable.
        """
        payload = {
            "cost_matrix_data": {
                "cost_matrix": {
                    0: matrix_data["matrix"]
                }
            },
            "fleet_data": {
                "vehicle_locations": constraints.get("vehicles", []),
                "vehicle_ids": constraints.get("vehicle_ids", ["robot_1"]),
            },
            "task_data": {
                "task_locations": constraints.get("tasks", []),
                "demand": constraints.get("demand", []),
            },
            "solver_config": {
                "time_limit": constraints.get("time_limit", 0.05),
            },
        }
        try:
            resp = requests.post(
                f"{self.base_url.rstrip('/')}/cuopt/routes",
                json=payload,
                timeout=self.timeout_s,
            )
            resp.raise_for_status()
            return self._map_solution(resp.json(), matrix_data["node_map"])
        except Exception as exc:  # noqa: BLE001 - want to catch connection + HTTP errors
            logger.warning("cuOpt unreachable, returning stub solution: %s", exc)
            return self._fallback_local_solve(matrix_data)

    def _map_solution(self, solution: Dict[str, Any], node_map: Dict[str, int]) -> Dict[str, Any]:
        idx_to_id = {v: k for k, v in node_map.items()}
        raw_routes = solution.get("response", {}).get("solver_response", {}).get("routes", {})
        routes = {}
        for vehicle_id, route_indices in raw_routes.items():
            routes[vehicle_id] = [idx_to_id.get(i, "?") for i in route_indices]
        return {"ok": True, "routes": routes, "source": "cuopt"}

    def _fallback_local_solve(self, matrix_data: Dict[str, Any]) -> Dict[str, Any]:
        # Minimal fallback: return empty route for a single robot.
        return {
            "ok": False,
            "reason": "solver_unreachable",
            "routes": {"robot_1": []},
        }


client = CuOptClient()
