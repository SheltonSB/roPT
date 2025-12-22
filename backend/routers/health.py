"""
health.py
What this file does:
- /health for edge readiness checks.
- Includes Mongo ping so you know persistence is alive.
"""

from fastapi import APIRouter
from ..db.mongo import get_db
from ..runtime_state import now_ms

router = APIRouter()

@router.get("/health")
async def health():
    # Mongo ping
    await get_db().command("ping")
    return {"ok": True, "ts_ms": now_ms()}
