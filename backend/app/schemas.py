# @Shelton Bumhe
# Assignment 3: Edge-to-Backend Communication
# This file handles all the data objects for our safety system.
# It makes sure the JSON we send back and forth actually makes sense.

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional


class SafetyEventIn(BaseModel):
    event_type: str
    ts_ms: int
    actor_id: str
    zone_id: str
    run_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class SafetyEventOut(SafetyEventIn):
    received_ms: int
    _id: Optional[str] = None


class ZoneDef(BaseModel):
    zone_id: str
    polygon: List[List[float]]  # [[x,y]...], image or world coords
    frame: Optional[str] = "cam_01"
    severity: Optional[str] = "soft"  # soft | emergency
    notes: Optional[str] = None


class ZonesPayload(BaseModel):
    zones: List[ZoneDef]


class RunStartIn(BaseModel):
    notes: Optional[str] = None


class RunStopIn(BaseModel):
    run_id: str
    notes: Optional[str] = None


class MetricIn(BaseModel):
    ts_ms: int
    run_id: Optional[str] = None
    pipeline_fps: float = 0.0
    gpu_util_pct: float = 0.0
    mem_util_pct: float = 0.0
    evt_to_backend_ms: float = 0.0
    cuopt_solve_ms: float = 0.0
    end_to_end_ms: float = 0.0
    notes: Optional[str] = None
