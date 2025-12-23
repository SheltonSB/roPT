#!/usr/bin/env bash
set -euo pipefail

# Simple launcher for the edge bridge. Expects BACKEND_URL env var (defaults to localhost:8000).
BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"

echo "Starting DeepStream → backend bridge -> ${BACKEND_URL}"
python ds_event_bridge.py --backend-url "${BACKEND_URL}"
