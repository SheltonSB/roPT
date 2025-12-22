#!/usr/bin/env bash
#Shelton bumhe 
# start_backend.sh
# What this file does:
# - Starts the backend locally (WSL) with venv and .env support.

set -euo pipefail
cd "$(dirname "$0")"

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

exec uvicorn app.api_server:app --host 0.0.0.0 --port 8000
