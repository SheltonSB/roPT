"""
ds_event_bridge.py
Lightweight bridge that forwards DeepStream-style JSON events to the backend.
For demo/dev it also supports a --demo flag to emit synthetic events.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Dict, Any

import requests


def post_event(backend_url: str, evt: Dict[str, Any]) -> None:
    url = f"{backend_url.rstrip('/')}/events"
    resp = requests.post(url, json=evt, timeout=2)
    resp.raise_for_status()


def run_demo(backend_url: str, actor_id: str) -> None:
    ts_ms = lambda: int(time.time() * 1000)
    events = [
        {"event_type": "ENTER", "actor_id": actor_id, "zone_id": "zone_A"},
        {"event_type": "MOVE", "actor_id": actor_id, "zone_id": "zone_B"},
        {"event_type": "EXIT", "actor_id": actor_id, "zone_id": "zone_B"},
    ]
    for e in events:
        e["ts_ms"] = ts_ms()
        post_event(backend_url, e)
        print(f"Sent event: {e}")
        time.sleep(0.5)


def stream_stdin(backend_url: str) -> None:
    """
    Forward newline-delimited JSON objects from stdin to the backend /events endpoint.
    """
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        evt = json.loads(line)
        if "ts_ms" not in evt:
            evt["ts_ms"] = int(time.time() * 1000)
        post_event(backend_url, evt)
        print(f"Forwarded event: {evt}")


def main():
    parser = argparse.ArgumentParser(description="Forward DeepStream events to backend.")
    parser.add_argument("--backend-url", required=True, help="Backend base URL (e.g. http://127.0.0.1:8000)")
    parser.add_argument("--demo", action="store_true", help="Send synthetic events instead of reading stdin")
    parser.add_argument("--actor-id", default="person_1", help="Actor ID for demo mode")
    args = parser.parse_args()

    if args.demo:
        run_demo(args.backend_url, args.actor_id)
    else:
        stream_stdin(args.backend_url)


if __name__ == "__main__":
    main()
