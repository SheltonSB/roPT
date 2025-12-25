"""
Compatibility shim.
The canonical RuntimeState/now_ms live in app.runtime_state; this file re-exports
them so older imports keep working while the codebase migrates to app/.
"""

from .app.runtime_state import ActorState, RuntimeState, RedisRuntimeState, now_ms

__all__ = ["ActorState", "RuntimeState", "RedisRuntimeState", "now_ms"]
