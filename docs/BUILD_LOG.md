# BUILD_LOG.md

## [2026-10-10] Project initialised (read this first)
### What changed
- Created `dormathon-workspace/` layout mirroring `pepperdex-workspace`: `adk-docs/`, `adk-python/` (v2.6.1), `sandbox/`, `pitch-and-design/`, `archive/`, project in `startupbuddy/`.
- Wrote CLAUDE.md, PLAN.md, MASTER_SHEET.md, README.md and docs (spec, data model, agents, MCP contract, WorkBuddy integration, problem statement, competitors, credentials, validation), rules skill, google-adk skill, WorkBuddy skill drafts.
### Why (decisions, owner, 2026-10-10)
- `startupbuddy/` folder; single `frontend/` with landing at `/`.
- **Task-queue** WorkBuddy integration, because MCP is client→server only (WorkBuddy = client).
- 16 agents: 1 coordinator, 9 BMC, 5 council, 1 advisor. Scope: Malaysia incl. Sarawak. Demo user, no auth.
### Verified
- WorkBuddy connector capabilities read from Tencent docs (URL + streamable HTTP + API-key auth; 30 s tool limit).
- ADK clone at tag matching installed `google-adk` 2.6.1.
### Still broken / unverified
- Everything in `../sandbox/EXPERIMENTS.md`. No code exists yet.
### Lesson
- Design every WorkBuddy-facing tool to return in ≤25 s; long work goes through the queue.

## [2026-10-10] Deliverables clarified; problem restated
### What changed
- Owner: submission is a **software demo video** (screen recording of the product), plus a slide deck and pitch script that correspond page for page. PLAN.md Phase E and `../pitch-and-design/README.md` updated.
- `docs/PROBLEM_STATEMENT.md`: added "What is happening now" (status quo, step by step) and a one-line version.

## [2026-10-10] No tunnel: WorkBuddy always talks to Cloud Run
### What changed
- Dropped `cloudflared`. Firebase Hosting serves only the frontend; the MCP server is on Cloud Run, which has its own public HTTPS URL. EXP-1/2/3 use a throwaway Cloud Run service `exp-mcp-echo`.
### Why
- One fewer tool; experiments test the same path as the demo. WorkBuddy and SSE use the direct Run URL because Firebase rewrites to Cloud Run cut off at ~60 s.

## [2026-10-10] Name line and tagline fixed
- Name line: "StartupBuddy - An agentic AI solution that takes aspiring Malaysian founders from a vague business idea to a locally validated, council-reviewed business model and their first booked stakeholder meetings, powered by Tencent WorkBuddy."
- Tagline: "From idea to first meeting." English only (no Malay version for now).
- Synced in CLAUDE.md, README.md, MASTER_SHEET.md, docs/PROJECT_SPEC.md (§1, landing hero), ../pitch-and-design/README.md.

## [2026-10-10 15:30 MYT] Deadline, team, accounts; pilot scope set
### What changed
- Deadline **2026-10-11 09:30 MYT**. Deliverables: repo link, landing page link, slide deck, documentation; 3-min pitch + 2-min Q&A; optional 30 s demo video. Approach: first pilot by the deadline, then refine (logged here).
- Team recorded (SMILING FACE WITH SUNGLASSES). Repo `nathanyap17/startupbuddy` added as git remote `origin` (not pushed).
- Account corrected to `demony11111@gmail.com` (DRAFT.md, PLAN.md, WORKSPACE_SETUP.md).
- gcloud, ADC quota project, Firebase (attached) and billing are ready.
- WorkBuddy MCP config is a JSON file (`~/.workbuddy-ai/mcp.json`), documented in WORKBUDDY_INTEGRATION.md.
- PLAN.md: pilot scope table and timeline; ADK pinned at 2.6.1 for the pilot.
### Still unverified
- EXP-1 (WorkBuddy to Cloud Run MCP) not yet run.

## [2026-10-10 15:45 MYT] Docs approved; APIs enabled
- Owner approved the docs; HOLD lifted (owner runs pushes/deploys).
- 12 Google Cloud APIs enabled on `dormathon-workspace-1`. WorkBuddy desktop version 5.7.6.
