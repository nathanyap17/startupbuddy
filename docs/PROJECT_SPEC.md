# PROJECT_SPEC.md: StartupBuddy

> Drafted 2026-10-10 from `../../DRAFT.md` and the owner's decisions in chat. Authoritative for behaviour; dated corrections go in place.

## 1 · Identity
- **Name:** StartupBuddy
- **Name line:** StartupBuddy - An agentic AI solution that takes aspiring Malaysian founders from a vague business idea to a locally validated, council-reviewed business model and their first booked stakeholder meetings, powered by Tencent WorkBuddy.
- **Tagline:** From idea to first meeting.
- **Track:** Dormathon Track 2, WorkBuddy Agentic Solutions
- **User:** aspiring founders in Malaysia (students, fresh graduates, would-be hawkers and micro-business owners), Sarawak included
- **Promise:** one sentence of intent → grounded problem statement → full Business Model Canvas → five-seat council verdict → approved first actions (meetings, drafts, folder)

## 2 · Problem
Summary here; full evidence and sources in `docs/PROBLEM_STATEMENT.md` and `MASTER_SHEET.md` §1.
Aspiring founders stop at a vague idea. They lack (a) **grounded local validation** (who buys, who already competes nearby, what licences apply) and (b) **a concrete path to the right local people and programmes**. Existing tools generate generic plans; the national portal (MYStartup) aggregates information but does not do the work with the founder.

## 3 · Components

| Component | Inputs | Outputs | Guardrails |
|---|---|---|---|
| Web app (`frontend/`) | user clicks, SSE | sessions, canvas, approvals, report viewer | no login (demo user) |
| API (`backend/app/routers`) | REST | JSON, SSE | Pydantic contracts |
| ADK pipeline (`backend/app/agent`) | session state, DB | DB rows + `agent_event` | gates in DB, bounded loops, per-turn timeout |
| WorkBuddy MCP (`backend/app/mcp/workbuddy_server.py`) | MCP calls | queue claims/results | API key, ≤25 s per call, schema validation |
| Task queue (`backend/app/workbuddy`) | enqueue / claim / submit | wakes waiting agent | lease, deadline, max 2 attempts, labelled fallback |
| Google Workspace MCP (`backend/app/mcp/gws_server.py`) | approved action ids | Calendar/Meet event, Gmail draft, Drive folder | refuses unapproved action ids (code check) |
| Hybrid RAG (`backend/app/rag`) | query, namespace | ranked chunks with `source_url` | sources always returned to the agent |
| External data tools (`backend/app/tools`) | place/query | competitor list, demographics | results stored as `evidence_item` with URLs |
| WorkBuddy skills (`workbuddy/skills`) | task inputs | JSON result + artifacts | must match `output_schema` |

## 4 · Flows

### 4.1 Start (either entry)
- **Web:** `/app` → "New session" → intent + location → `POST /sessions` → pipeline starts.
- **WorkBuddy:** user types *"Use StartupBuddy: I want to sell kolo mee near Padungan, Kuching"* → skill `startupbuddy-worker` calls `start_session`, gives the user the `app_url`, then enters its worker loop.

### 4.2 Main run
1. **Phase 1:** `problem_coordinator` geocodes, calls `places_nearby` (competitors, ratings, review counts), `opendosm_lookup` (district population, income), `search_knowledge` (licensing/programmes), enqueues `desk_research` for WorkBuddy, then writes problem statement + evidence. → **G1** card in web app (and WorkBuddy can relay via `confirm_gate`).
2. **Phase 2:** BMC waves 1→2→3. Each block node on the canvas animates `thinking` → `done`; edges appear when a block reads another.
3. **Phase 3:** council (5 parallel) → deterministic aggregation → revise weak blocks (≤2 rounds) → enqueue `report_builder`, `financial_sheet`, `one_pager`.
4. **Phase 4:** `advisor` proposes `action_item`s, each citing the decision it came from → **G2** approvals → executes approved items via Google Workspace MCP → records `external_ref`.
5. **Follow-up:** session shows a checklist of `must_verify` items and scheduled meetings; the user marks them done (no automation after that in v1).

### 4.3 Fallbacks
- WorkBuddy task expired → agent proceeds with its own output, records `agent_event(kind=fallback)` and labels affected evidence `needs_verification`.
- Model turn timeout (`AGENT_TURN_TIMEOUT_S`) → block marked `revising` with an error note; pipeline continues; council sees the gap.
- Seeded complete demo session available from the landing page for judges if the live run is slow.

## 5 · Agent topology
See `docs/AGENTS.md`.

## 6 · Non-negotiables
See `CLAUDE.md` and `.claude/skills/startupbuddy-rules/SKILL.md`.

## 7 · Deployment
Cloud Run `startupbuddy-api` (region `asia-southeast1`, `--min-instances 1` during demo, timeout 3600 s for SSE), Cloud SQL Postgres 16 `startupbuddy-db` with `vector` extension, GCS bucket `startupbuddy-artifacts`, Firebase Hosting on project `dormathon-workspace-1`. WorkBuddy connector URL `https://<run-url>/mcp`.

## 8 · UI screens

### 8.1 Landing (`/`)
Hero: name line + tagline (verbatim from §1). Purpose: explain in 10 s, link to the web app, show "how it works with WorkBuddy". Buttons: *Open demo app* · *Watch demo video* · *GitHub* · *Connect WorkBuddy (guide)*.

### 8.2 Sessions (`/app`)
| Field | Type | Source | Notes |
|---|---|---|---|
| title | text | `startup_session.title` | |
| phase | enum | `startup_session.phase` | badge |
| origin | text | `startup_session.origin` | WorkBuddy icon if started there |
| updated_at | time | | Asia/Kuching |

### 8.3 Session workspace (`/app/s/:id`)
Three panes:
- **Left: timeline**, the `agent_event` feed (agent, summary, latency), filterable.
- **Centre: canvas** (React Flow). Nodes: Problem → 9 BMC blocks (BMC layout) → 5 council seats → Advisor. Node states: idle, thinking (pulsing), done, revising, fallback. Edges animate on `handoff`/reads. A WorkBuddy node shows queued/claimed tasks.
- **Right: inspector**, the selected node's content, evidence items with labels, council notes.
- **Gate cards:** G1 (confirm/edit problem), G2 (per-action approve/reject).

### 8.4 Report (`/app/s/:id/report`)
Problem, canvas, council verdict, "measure / improve / verify" tables, artifacts list (DOCX/XLSX/PPTX links), actions taken.

## 9 · API contract (REST; MCP in `docs/MCP_CONTRACT.md`)
| Method | Path | Body / query | Response |
|---|---|---|---|
| GET | `/health` | | `{ok, db, model}` |
| GET | `/sessions` | | `SessionSummary[]` |
| POST | `/sessions` | `{intent, location_text}` | `SessionSummary` |
| GET | `/sessions/{id}` | | `SessionDetail` (problem, blocks, verdict, actions, artifacts) |
| GET | `/sessions/{id}/events` | SSE, `Last-Event-ID` | `AgentEvent` stream |
| POST | `/sessions/{id}/gates/{gate}` | `{decision, notes?, action_ids?}` | `{ok}` |
| DELETE | `/sessions/{id}` | | `{ok}` |
| GET | `/sessions/{id}/report` | | `Report` |

Models live in `backend/app/schemas/`; frontend types generated from `/openapi.json`.
