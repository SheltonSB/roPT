"""
health.py
Provides /health for edge readiness checks.
Includes Mongo ping so persistence is validated.
"""

from fastapi import APIRouter

from ..db.mongo import get_db
from ..runtime_state import now_ms
from ..cuopt_client import client as cuopt_client

router = APIRouter()


@router.get("/health")
async def health():
    await get_db().command("ping")
    cuopt = cuopt_client.health_check()
    return {"ok": True, "ts_ms": now_ms(), "cuopt": cuopt}


@router.get("/health/ready")
async def ready():
    await get_db().command("ping")
    cuopt = cuopt_client.health_check()
    ok = bool(cuopt.get("ok"))
    return {"ok": ok, "ts_ms": now_ms(), "cuopt": cuopt}
