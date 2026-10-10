# backend/

FastAPI + Google ADK (scaffolded in Phase B). Layout mirrors PepperDex:

| Path | Holds |
|---|---|
| `app/agent/prompts.py` | instructions for the 16 agents |
| `app/agent/factories.py` | agent factories (coordinator, 9 BMC, 5 council, advisor) + deterministic council aggregation |
| `app/agent/pipeline.py` | phases, gates G1/G2, BMC waves, WorkBuddy handoffs, fallbacks |
| `app/agent/common.py` | run an ADK agent with timeout, tool-call logging, structured-output parsing |
| `app/mcp/workbuddy_server.py` | WorkBuddy MCP tools at `/mcp` (X-API-Key) |
| `app/mcp/gws.py` | Google Calendar (+Meet) / Gmail draft actions, approval-checked |
| `app/workbuddy/` | task queue + output schemas |
| `app/rag/search.py` | knowledge ingest + full-text search (vector half post-pilot) |
| `app/tools/places.py` | Google Places (New) geocode + nearby competitors (ADC auth, no API key) |
| `app/routers/sessions.py` | REST, SSE events, gates, report markdown, artifacts |

Run locally: `docker compose up -d db` (host port **5433**), then `uv run uvicorn app.main:app --port 8000`.
Test without WorkBuddy: `python ../../sandbox/sim_worker.py http://localhost:8000 <MCP_API_KEY>`.
