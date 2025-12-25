# roPT
ROPT is a real-time safety-aware routing system that detects when people enter restricted zones and automatically re-routes robots to avoid unsafe paths. It turns perception into semantic safety events, updates a workspace graph in real time, and computes new routes under tight latency constraints using dynamic forbidden edges and risk penalties.

## Quickstart (dev)
1) Start Mongo + backend: `cd docker && docker compose -f compose.dev.yml up --build`
2) In another shell, hit health: `curl http://127.0.0.1:8000/health`
3) Send a demo event from edge: `cd edge/deepstream && BACKEND_URL=http://127.0.0.1:8000 python ds_event_bridge.py --demo`
4) Inspect state: `curl http://127.0.0.1:8000/state`

## Notes
- Backend entrypoint is `app.main:app` (async, Mongo-backed).
- Edge bridge accepts newline-delimited JSON on stdin or `--demo` synthetic events.

## Dashboard
1) `cd dashboard`
2) `npm install`
3) `npm run dev`
4) Open `http://127.0.0.1:5173` and ensure the backend is running.
