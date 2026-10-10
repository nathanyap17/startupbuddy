# StartupBuddy

StartupBuddy - An agentic AI solution that takes aspiring Malaysian founders from a vague business idea to a locally validated, council-reviewed business model and their first booked stakeholder meetings, powered by Tencent WorkBuddy.
**From idea to first meeting.**

> Name line + tagline are fixed (owner, 2026-10-10). Copy them verbatim into the landing page, deck title slide and pitch. English only.

**Context:** Dormathon, Track 2: WorkBuddy Agentic Solutions. **Tencent WorkBuddy is mandatory** for the project, the slides and the documentation. WorkBuddy credits are provided; there are no Kiro or Grafilab credits. The original brief is `../DRAFT.md`.
**Team:** SMILING FACE WITH SUNGLASSES: Nathan Yap (leader), Abraham Pang, Malcolm Sim, Zoe Tan.
**Deadline:** submission 2026-10-11 09:30 MYT (repo link, landing page link, slide deck, documentation; 3-min pitch + 2-min Q&A; optional 30 s demo video). Pilot first, refine after (log in `docs/BUILD_LOG.md`).

> **Read `PLAN.md` before starting any task.** `docs/PROJECT_SPEC.md` holds the system design, `docs/DATA_MODEL.md` the schema, `docs/MCP_CONTRACT.md` the WorkBuddy-facing tools, `docs/AGENTS.md` the agent roster and `docs/CREDENTIALS.md` every environment variable (names only). If two documents disagree, the more recently dated correction wins. Flag the conflict rather than silently picking one.

## The one-sentence product

Existing tools write a business plan *for* you from a generic template. StartupBuddy grounds the idea in **your actual neighbourhood** (competitors on the map, local demand, Malaysian licensing and programmes), builds the canvas with **16 collaborating agents you can watch**, has a **simulated customer, CEO, investor, CFO and mentor** cross-examine it, and then **books the first real meetings** (with your approval) through WorkBuddy and Google Workspace.

## Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite + TypeScript, React Flow (live canvas). Landing page at `/`, web app at `/app`. Firebase Hosting |
| Backend | FastAPI (Python 3.11+), Pydantic v2, SQLAlchemy 2.0 async. Cloud Run (`asia-southeast1`) |
| Agents | Google ADK (`google-adk`, pinned; see `WORKSPACE_SETUP.md`) + Vertex AI Gemini (explicit model ID, no `-latest` alias) |
| Data | PostgreSQL 16 + pgvector. Local: Docker. Cloud: Cloud SQL |
| Retrieval | Hybrid search: pgvector cosine + Postgres full-text, fused by reciprocal rank fusion (RRF) |
| Embeddings | EmbeddingGemma (default, per owner) vs Vertex Gemini embeddings. Decided by EXP-5 |
| WorkBuddy link | Our MCP server (streamable HTTP, API-key header) added as a WorkBuddy custom connector. **Task-queue pattern** (below) |
| Advisor actions | Google Workspace MCP server in our backend (Calendar, Meet, Gmail **drafts**, Drive), approval-gated |
| Maps / data | Google Places API (New) for nearby competitors. OpenDOSM for demographics (EXP-6) |

## Architecture

```
          ┌──────────── StartupBuddy web app (Firebase) ────────────┐
          │ sessions · live canvas (SSE) · approvals · report       │
          └───────────────▲──────────────────────┬──────────────────┘
                          │ SSE / REST           │ REST
┌─────────────────────────┴──────────────────────▼──────────────────────────┐
│ FastAPI on Cloud Run                                                      │
│  ADK Pipeline: Phase1 ProblemCoordinator → ⏸G1 → Phase2 BMC (9, 3 waves) │
│                → Phase3 Council (5) ⟲ max 2 revisions → Phase4 Advisor ⏸G2│
│  tools: Places · OpenDOSM · hybrid RAG · enqueue_workbuddy_task          │
│  /mcp  (WorkBuddy-facing)     /mcp-gws (Google Workspace, Advisor only)   │
│  Postgres: sessions · canvas · evidence · workbuddy_task queue · kb       │
└───────────────▲───────────────────────────────────────────────────────────┘
                │ MCP (streamable HTTP, X-API-Key)
     Tencent WorkBuddy desktop: skill `startupbuddy-worker`
     loop: await_next_task → run task skill → submit_task_result
```

**Task-queue pattern (decided 2026-10-10).** MCP only lets WorkBuddy call us; we cannot call into WorkBuddy. So ADK agents *enqueue* a `workbuddy_task` (skill name and inputs). WorkBuddy, running the `startupbuddy-worker` skill, long-polls `await_next_task` (≤25 s per call, under WorkBuddy's ~30 s tool limit), runs the named skill and posts `submit_task_result`. The backend wakes the waiting agent and streams the result to the canvas.

## Non-negotiable rules

Full list with examples: `.claude/skills/startupbuddy-rules/SKILL.md`.
1. **No outward action without explicit approval.** The Advisor runs Google Workspace tools only on actions the user approved in gate G2. Emails are **drafted, never sent** automatically.
2. **Every figure in a report carries an evidence label:** `sourced` (with URL), `estimated` (with method) or `needs_verification`. An LLM may not present an unsourced number as fact.
3. **No scraping personal contact data.** "Connect with stakeholders" means curated public programmes and organisations from `knowledge/`, plus people the user names themselves.
4. **Agents never block forever on WorkBuddy.** Every enqueued task has a deadline. On expiry the agent continues with a labelled fallback, and the canvas shows the degradation.
5. **Loops are bounded.** Council→BMC revision ≤ 2 rounds; any `LoopAgent` has `max_iterations`.
6. **Secrets never in the repo or docs.** Names only in `docs/CREDENTIALS.md`.

## Conventions

- **One contract:** Pydantic models in `backend/app/schemas/` are the source of truth. Frontend types are generated from FastAPI's OpenAPI (`openapi-typescript`). Never hand-write duplicates.
- **Configuration switches environments**, not code: `DATABASE_URL`, `GEMINI_MODEL`, `EMBEDDING_BACKEND`, `PUBLIC_BASE_URL`.
- **Deterministic checks around AI:** council scores are aggregated by plain code, and gate decisions come from DB state, not LLM text.
- **Log every agent/tool call** to `agent_event` (inputs summary, latency, result summary). The same table feeds the live canvas, which serves as demo evidence.
- **IDs:** ULID strings. **Timestamps:** stored UTC, displayed in `Asia/Kuching` (UTC+8).
- **Before writing ADK code, read the `google-adk` skill**; it points at `../adk-python` at the pinned tag. Don't guess signatures.
- **Ownership:** the owner runs logins (`gcloud`, `firebase`, WorkBuddy), deploys and pushes. Claude prepares the exact command.

## Deployment targets

| | LOCAL | CLOUD |
|---|---|---|
| Backend | `uvicorn` on :8000 | Cloud Run `startupbuddy-api` |
| DB | Docker `pgvector/pgvector:pg16` on :5433 (host; a native Postgres uses 5432) | Cloud SQL `startupbuddy-db` |
| Frontend | Vite on :5173 | Firebase Hosting (project `dormathon-workspace-1`) |
| WorkBuddy MCP URL | n/a: WorkBuddy can't reach localhost; test WorkBuddy against Cloud Run | `https://<run-url>/mcp` (direct Run URL, **not** via Firebase rewrite: ~60 s cut-off breaks SSE) |

Switching is configuration only. Never break LOCAL to enable CLOUD.

## Commands

```bash
docker compose up -d db                                   # Postgres + pgvector
cd backend && uv run uvicorn app.main:app --reload        # API + MCP on :8000
cd frontend && npm run dev                                # web on :5173
cd backend && uv run pytest -q                            # tests
./deploy-cloud.sh                                         # Cloud Run (owner runs)
cd frontend && npm run build && firebase deploy --only hosting   # owner runs
```
*(Commands become valid once Phase B scaffolds the code.)*

## What to never cut

The one-prompt end-to-end run · WorkBuddy doing real work through the task queue · the live canvas branching as agents work · the council verdict with evidence labels · the approval gate before Google Workspace actions.

## Shipping status

2026-10-10: docs and folder structure only. No code, no deploys. Not yet a pushed GitHub repo (owner reviews first).
