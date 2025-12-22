"""
@Shelton Bumhe
metrics.py
What this file does:
- Stores/query performance metrics in MongoDB.
"""

from fastapi import APIRouter
from ..schemas import MetricIn
from ..repos import metrics_repo
from ..runtime_state import now_ms

router = APIRouter()

@router.post("/metrics")
async def ingest_metric(m: MetricIn):
    doc = m.model_dump()
    doc["received_ms"] = now_ms()
    _id = await metrics_repo.insert_metric(doc)
    return {"ok": True, "_id": _id}

@router.get("/metrics")
async def get_metrics(run_id: str | None = None, limit: int = 500):
    return {"metrics": await metrics_repo.query_metrics(run_id=run_id, limit=limit)}
