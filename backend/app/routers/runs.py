"""
runs.py
Creates/stops runs so events/metrics can be tagged for replay.
"""

from fastapi import APIRouter

from ..schemas import RunStartIn, RunStopIn
from ..repos import runs_repo
from ..runtime_state import RuntimeState

router = APIRouter()


def bind_state(state: RuntimeState):
    router.state_ref = state


@router.post("/runs/start")
async def start_run(body: RunStartIn):
    run_id = await runs_repo.start_run(body.notes)
    router.state_ref.active_run_id = run_id
    return {"ok": True, "run_id": run_id}


@router.post("/runs/stop")
async def stop_run(body: RunStopIn):
    out = await runs_repo.stop_run(body.run_id, body.notes)
    if router.state_ref.active_run_id == body.run_id:
        router.state_ref.active_run_id = None
    return out


@router.get("/runs")
async def list_runs(limit: int = 50):
    return {"runs": await runs_repo.list_runs(limit=limit)}
