"""
@author: Shelton Bumhe
db/mongo.py
What this file does:
- Creates the async MongoDB client (Motor).
- Defines collections.
- Builds indexes at startup (so queries are fast and real).
"""

from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from typing import Optional

from ..config import settings

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongo_uri)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    global _db
    if _db is None:
        _db = get_client()[settings.mongo_db]
    return _db


def col_zones():
    return get_db()["zones"]


def col_events():
    return get_db()["events"]


def col_metrics():
    return get_db()["metrics"]


def col_runs():
    return get_db()["runs"]


async def ensure_indexes() -> None:
    # Zones: unique zone_id
    await col_zones().create_index([("zone_id", ASCENDING)], unique=True)

    # Runs: latest first
    await col_runs().create_index([("started_at_ms", DESCENDING)])

    # Events: query by run and time, also by zone/time
    await col_events().create_index([("run_id", ASCENDING), ("ts_ms", ASCENDING)])
    await col_events().create_index([("zone_id", ASCENDING), ("ts_ms", ASCENDING)])
    await col_events().create_index([("actor_id", ASCENDING), ("ts_ms", ASCENDING)])

    # Metrics: query by run and time
    await col_metrics().create_index([("run_id", ASCENDING), ("ts_ms", ASCENDING)])
