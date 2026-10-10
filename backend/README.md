# backend/

FastAPI + Google ADK (scaffolded in Phase B). Layout mirrors PepperDex:

| Path | Holds |
|---|---|
| `app/agent/coordinator/` | `problem_coordinator` |
| `app/agent/bmc/` | 9 BMC agents + wave orchestration |
| `app/agent/council/` | 5 council seats + deterministic aggregation |
| `app/agent/advisor/` | advisor + Google Workspace MCP client |
| `app/mcp/` | `workbuddy_server.py` (`/mcp`), `gws_server.py` (`/mcp-gws`) |
| `app/workbuddy/` | task queue (enqueue / claim / submit / expire) + output schemas |
| `app/rag/` | ingest + hybrid search (pgvector + full-text, RRF) |
| `app/tools/` | Places, OpenDOSM, geocoding |
| `app/routers/` `app/schemas/` `app/models/` | REST, Pydantic contracts, SQLAlchemy models |
| `seed/` `tests/` `scripts/` | demo user + seeded session, pytest, ingest/maintenance |
