"""
ws.py
WebSocket connection manager for broadcasting state snapshots.
"""

from __future__ import annotations

from typing import Set, Optional
import json

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self, redis_client: Optional[object] = None, channel: str = "ropt:ws"):
        self._connections: Set[WebSocket] = set()
        self._redis = redis_client
        self._channel = channel

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast_json(self, payload: dict) -> None:
        if self._redis is not None:
            await self._redis.publish(self._channel, json.dumps(payload))
            return
        await self._broadcast_local(payload)

    async def _broadcast_local(self, payload: dict) -> None:
        dead = []
        for ws in self._connections:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def start_redis_listener(self) -> None:
        if self._redis is None:
            return
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(self._channel)
        async for msg in pubsub.listen():
            if msg.get("type") != "message":
                continue
            try:
                payload = json.loads(msg.get("data"))
            except Exception:
                continue
            await self._broadcast_local(payload)
