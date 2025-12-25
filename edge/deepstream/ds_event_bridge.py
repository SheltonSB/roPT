"""
ds_event_bridge.py
Lightweight bridge that forwards DeepStream-style JSON events to the backend.
For demo/dev it also supports a --demo flag to emit synthetic events.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import sqlite3
import sys
import threading
import time
from typing import Dict, Any

import requests


def init_buffer(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS event_buffer ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "payload TEXT NOT NULL"
        ")"
    )
    conn.commit()
    return conn


def buffer_event(conn: sqlite3.Connection, evt: Dict[str, Any]) -> None:
    conn.execute("INSERT INTO event_buffer (payload) VALUES (?)", (json.dumps(evt),))
    conn.commit()


def pop_buffered_event(conn: sqlite3.Connection) -> Dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, payload FROM event_buffer ORDER BY id ASC LIMIT 1"
    ).fetchone()
    if not row:
        return None
    evt_id, payload = row
    conn.execute("DELETE FROM event_buffer WHERE id = ?", (evt_id,))
    conn.commit()
    return json.loads(payload)


def post_event(backend_url: str, evt: Dict[str, Any]) -> None:
    url = f"{backend_url.rstrip('/')}/events"
    resp = requests.post(url, json=evt, timeout=2)
    resp.raise_for_status()


def start_event_worker(backend_url: str, db_path: str) -> "queue.Queue[dict]":
    q: "queue.Queue[dict]" = queue.Queue(maxsize=5000)
    conn = init_buffer(db_path)

    def worker():
        backoff_s = 0.5
        while True:
            buffered = pop_buffered_event(conn)
            if buffered:
                try:
                    post_event(backend_url, buffered)
                    backoff_s = 0.5
                except Exception:
                    buffer_event(conn, buffered)
                    time.sleep(backoff_s)
                    backoff_s = min(backoff_s * 2, 5.0)
                    continue
            try:
                evt = q.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                post_event(backend_url, evt)
                backoff_s = 0.5
            except Exception:
                buffer_event(conn, evt)
                time.sleep(backoff_s)
                backoff_s = min(backoff_s * 2, 5.0)
            finally:
                q.task_done()

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return q


def run_demo(backend_url: str, actor_id: str, q: "queue.Queue[dict]") -> None:
    ts_ms = lambda: int(time.time() * 1000)
    events = [
        {"event_type": "ENTER", "actor_id": actor_id, "zone_id": "zone_A"},
        {"event_type": "MOVE", "actor_id": actor_id, "zone_id": "zone_B"},
        {"event_type": "EXIT", "actor_id": actor_id, "zone_id": "zone_B"},
    ]
    for e in events:
        e["ts_ms"] = ts_ms()
        try:
            q.put_nowait(e)
        except queue.Full:
            pass
        print(f"Sent event: {e}")
        time.sleep(0.5)


def stream_stdin(backend_url: str, q: "queue.Queue[dict]") -> None:
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
        try:
            q.put_nowait(evt)
        except queue.Full:
            pass
        print(f"Forwarded event: {evt}")


def main():
    parser = argparse.ArgumentParser(description="Forward DeepStream events to backend.")
    parser.add_argument("--backend-url", required=True, help="Backend base URL (e.g. http://127.0.0.1:8000)")
    parser.add_argument("--demo", action="store_true", help="Send synthetic events instead of reading stdin")
    parser.add_argument("--actor-id", default="person_1", help="Actor ID for demo mode")
    parser.add_argument(
        "--buffer-db",
        default=os.environ.get("ROPT_EDGE_BUFFER_DB", "event_buffer.sqlite"),
        help="SQLite buffer path for store-and-forward",
    )
    args = parser.parse_args()

    q = start_event_worker(args.backend_url, args.buffer_db)
    if args.demo:
        run_demo(args.backend_url, args.actor_id, q)
    else:
        stream_stdin(args.backend_url, q)


if __name__ == "__main__":
    main()
