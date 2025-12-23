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

    def solve(self, graph: Dict[str, Any], constraints: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a routing request to cuOpt. Falls back to a pass-through plan if
        the cuOpt service is unavailable.
        """
        payload = {"graph": graph, "constraints": constraints}
        try:
            resp = requests.post(
                f"{self.base_url}/solve", json=payload, timeout=self.timeout_s
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001 - want to catch connection + HTTP errors
            logger.warning("cuOpt unreachable, returning stub solution: %s", exc)
            return self._stub_solution(graph)

    def _stub_solution(self, graph: Dict[str, Any]) -> Dict[str, Any]:
        # Return a simple identity route when no solver is present.
        nodes: List[str] = graph.get("nodes", [])
        return {
            "ok": False,
            "reason": "cuopt_unreachable",
            "route": nodes,
        }


client = CuOptClient()
