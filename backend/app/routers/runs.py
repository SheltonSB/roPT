"""
runs.py
Creates/stops runs so events/metrics can be tagged for replay.
"""

from fastapi import APIRouter, Depends, Query

from ..schemas import RunStartIn, RunStopIn
from ..repos import runs_repo
from ..runtime_state import RuntimeState
from ..deps import get_state

router = APIRouter()


@router.post("/runs/start")
async def start_run(body: RunStartIn, state: RuntimeState = Depends(get_state)):
    run_id = await runs_repo.start_run(body.notes)
    await state.set_active_run_id(run_id)
    return {"ok": True, "run_id": run_id}


@router.post("/runs/stop")
async def stop_run(body: RunStopIn, state: RuntimeState = Depends(get_state)):
    out = await runs_repo.stop_run(body.run_id, body.notes)
    active = await state.get_active_run_id()
    if active == body.run_id:
        await state.set_active_run_id(None)
    return out


@router.get("/runs")
async def list_runs(limit: int = Query(50, ge=1, le=1000)):
    return {"runs": await runs_repo.list_runs(limit=limit)}
