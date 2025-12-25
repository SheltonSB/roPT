# roPT
Real-time safety routing for robots working around people. roPT turns perception into safety decisions fast enough to keep fleets moving while enforcing human safety zones.

## Why it matters
Factories are dynamic. A person steps into a restricted zone and a robot path becomes unsafe immediately. roPT is built to respond in real time, not after-the-fact.

## At a glance
- Detects safety zone violations and updates routes in real time.
- Keeps an auditable event history without slowing decisions.
- Streams live state to a dashboard for operators and judges.

## What makes it different
- Hierarchical planning: global assignment plus local motion safety.
- VRP solver assigns tasks to the right robot.
- High-frequency Dijkstra-based planner evaluates alternatives in milliseconds.
- Precomputed distance matrix enables ~100 trajectory deviations/sec without CPU bottlenecks.

## Live demo flow
1) Edge perception emits zone events.
2) Backend queues events, updates live state, and writes to MongoDB.
3) Dashboard streams WebSocket snapshots and renders zones + actors.

## Key capabilities
- Real-time event ingestion and state snapshotting.
- MongoDB-backed audit trail for events, zones, runs, and metrics.
- WebSocket broadcasting for live UI.
- Structured APIs for zones, runs, and performance metrics.

## Repository layout
- `backend/` FastAPI app, Mongo persistence, WebSocket stream.
- `edge/` Event bridge and DeepStream integration.
- `dashboard/` React (Vite) live dashboard.
- `docker/` Docker Compose for Mongo + backend.

## Tech stack
- Backend: FastAPI, Motor/MongoDB, WebSocket streaming.
- Edge: DeepStream event bridge (stdin or demo).
- Frontend: React + Vite dashboard.

## Quickstart (Docker, recommended)
1) Start Mongo + backend:
   - `cd docker`
   - `docker compose -f compose.dev.yml up --build`
2) Check health:
   - `curl http://127.0.0.1:8000/health`
3) Send demo events:
   - `cd edge/deepstream`
   - `BACKEND_URL=http://127.0.0.1:8000 python ds_event_bridge.py --demo`
4) Inspect state:
   - `curl http://127.0.0.1:8000/state`

## Local backend (no Docker)
Requirements: Python 3.11+, MongoDB running on `127.0.0.1:27017`.
1) `cd backend`
2) `python -m pip install -r requirements.txt`
3) `python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

## Dashboard
Requirements: Node.js 18+.
1) `cd dashboard`
2) `npm install`
3) `npm run dev`
4) Open `http://127.0.0.1:5173`

To point the dashboard at another backend:
- `VITE_API_BASE=http://<host>:<port>`
Optional map sizing (to match DeepStream coordinates):
- `VITE_FRAME_WIDTH=1280`
- `VITE_FRAME_HEIGHT=720`

## DeepStream pad probe (edge -> backend)
If you are running DeepStream, use the Python pad probe script instead of `deepstream-app`.
It computes the "feet" point (bottom-center of the bounding box), checks zone polygons,
and posts ENTER/EXIT events to the backend.

Bandwidth control: the probe only emits events on zone transitions (ENTER/EXIT), not every frame.

Example:
```
cd edge/deepstream
python ropt_pad_probe.py \
  --backend-url http://127.0.0.1:8000 \
  --zones-from-backend \
  --uri file:///opt/nvidia/deepstream/deepstream-8.0/samples/streams/sample_720p.h264
```

Dependencies:
- DeepStream Python bindings (`pyds`)
- `shapely` for polygon tests

## Key API endpoints
- `GET /health` Health check (includes Mongo ping).
- `GET /state` Live state snapshot.
- `POST /events` Ingest safety events (queued).
- `GET /events` Query stored events.
- `GET /zones`, `PUT /zones` Manage zone polygons.
- `POST /runs/start`, `POST /runs/stop`, `GET /runs` Run lifecycle.
- `POST /metrics`, `GET /metrics` Perf metrics.
- `GET /ws` WebSocket stream of live snapshots.

## Event format (edge -> backend)
Example JSON:
```json
{
  "event_type": "ENTER",
  "ts_ms": 1700000000000,
  "actor_id": "person_1",
  "zone_id": "zone_A",
  "run_id": "optional_run_id",
  "payload": {}
}
```

## Environment variables
Set via `.env` or environment:
- `ROPT_BACKEND_HOST` (default `0.0.0.0`)
- `ROPT_BACKEND_PORT` (default `8000`)
- `ROPT_MONGO_URI` (default `mongodb://127.0.0.1:27017`)
- `ROPT_MONGO_DB` (default `ropt`)
- `ROPT_CUOPT_URL` (default `http://127.0.0.1:5000`)
- `ROPT_CUOPT_TIMEOUT_S` (default `0.05`)
- `ROPT_EVENT_QUEUE_MAX` (default `20000`)
- `ROPT_MAX_EVENTS` (default `5000`)

## Notes
- Backend entrypoint is `app.main:app` (async, Mongo-backed).
- Edge bridge accepts newline-delimited JSON on stdin or `--demo` synthetic events.
- cuOpt client is stubbed if the solver is unreachable.
- CORS is open for hackathon use; restrict `allow_origins` to the dashboard host in production.

## Troubleshooting
- If `/health` fails, verify MongoDB is running and reachable.
- If the dashboard is blank, ensure `VITE_API_BASE` points to the backend.
- If WebSocket stays "offline", check CORS and that `/ws` is reachable.
