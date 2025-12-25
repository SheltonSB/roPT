## 2025-12-22
- Switched backend Docker entrypoint to `app.main` (async + Mongo).
- Filled edge bridge with a simple stdin/demo forwarder to `/events`.
- Added stub cuOpt client so routing calls don’t crash when service is absent.

## 2025-12-23
- Unified backend entrypoint to `app.main` and added WebSocket broadcasting.
- Added a React dashboard for real-time zones + actors.
