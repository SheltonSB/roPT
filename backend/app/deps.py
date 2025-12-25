"""
deps.py
FastAPI dependency helpers for shared app state.
"""

from __future__ import annotations

from fastapi import Request, Header, HTTPException

from .runtime_state import RuntimeState
from .config import settings
from .planning import GraphManager, SpatialManager
from .schemas import SafetyEventIn
import asyncio


def get_state(request: Request) -> RuntimeState:
    return request.app.state.runtime_state


def get_queue(request: Request) -> "asyncio.Queue[SafetyEventIn]":
    return request.app.state.event_queue


def get_graph_manager(request: Request) -> GraphManager:
    return request.app.state.graph_manager


def get_spatial_manager(request: Request) -> SpatialManager:
    return request.app.state.spatial_manager


def require_edge_key(x_api_key: str | None = Header(default=None)) -> None:
    if settings.edge_api_key and x_api_key != settings.edge_api_key:
        raise HTTPException(status_code=401, detail="invalid edge api key")


def require_dashboard_key(x_api_key: str | None = Header(default=None)) -> None:
    if settings.dashboard_api_key and x_api_key != settings.dashboard_api_key:
        raise HTTPException(status_code=401, detail="invalid dashboard api key")
