"""
deps.py
FastAPI dependency helpers for shared app state.
"""

from __future__ import annotations

from fastapi import Request

from .runtime_state import RuntimeState
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
