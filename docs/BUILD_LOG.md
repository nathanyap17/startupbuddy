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

## [2026-10-10 16:30 MYT] EXP-1 and EXP-2 passed: WorkBuddy task queue is viable
### Verified
- Throwaway server `exp-mcp-echo` on Cloud Run (mcp 2.2.0 `MCPServer`, stateless streamable HTTP, `X-API-Key`).
- WorkBuddy 5.7.6 connected via `mcp.json` (`"type": "http"`, header). 3/3 tools enabled.
- One WorkBuddy turn: 10 long-polls (`wait_s=20`), 3 dummy tasks received and submitted correctly; 14.02 credits, about 4 min.
### Lesson
- URL must end in `/mcp` (else 404 "SSE error").
- Idle polls cost credits (~1.4 each): cap idle polls at 20; enqueue WorkBuddy tasks in bursts.
### Next
- Delete `exp-mcp-echo` once the real backend is deployed.

## [2026-10-10 17:05 MYT] Backend pilot: full pipeline runs locally
### What changed
- FastAPI + ADK 2.6.1 backend: models (create_all), WorkBuddy queue + `/mcp` (9 tools), 16 agents, pipeline with G1/G2, Places tool, KB search, Calendar/Gmail-draft actions (approval-checked), REST + SSE, report markdown.
- Local Postgres on host port **5433** (a native Postgres occupies 5432).
- Gemini `gemini-3.5-flash` @ `global`, `thinking_level=LOW` (default thinking timed out the coordinator at 150 s).
### Verified (local, simulated WorkBuddy worker `sandbox/sim_worker.py` over real `/mcp`)
- Kolo mee @ Padungan: Phase 1 to G1; after approval 9 blocks, 5 council reviews (2 go / 3 revise → overall revise), 4 advisor actions, 33 evidence items (12 sourced / 13 estimated / 8 needs_verification), both WorkBuddy tasks succeeded. ~129 s from G1 to G2.
### Still unverified
- Real WorkBuddy doing desk_research / report_builder (EXP-3); Google Workspace actions (needs `client_secret.json` + token); Cloud Run deploy; frontend.
### Pilot deviations from docs
- REST responses are dicts, not shared Pydantic response models (one-contract rule deferred); no Alembic; full-text search only; council revision loop not run (single pass).

## [2026-10-10 17:55 MYT] Frontend + deploy scripts
### What changed
- React/Vite frontend: landing (`/`), sessions (`/app`), live canvas workspace with SSE timeline, inspector, G1/G2 cards (`/app/s/:id`), report (`/app/s/:id/report`, raw HTML stripped).
- Deploy: root `Dockerfile` (uv, Python 3.12, includes `knowledge/`), `.gcloudignore`, `firebase.json` (SPA rewrite), `infra/setup-cloud.ps1` (DB, user, secrets, IAM), `infra/deploy-backend.ps1` (Cloud Run `startupbuddy-api`, min=max=1, Cloud SQL socket, secrets), `infra/deploy-frontend.ps1`.
- WorkBuddy skills v0.2: exact `mcp__startupbuddy__*` tool names; worker relays G1/G2 via `get_session_status`/`confirm_gate`; report builder returns `report_markdown` + local DOCX path (via WorkBuddy's minimax-docx skill).
### Verified
- `npm run build` OK; canvas renders a completed session (16 agent nodes + WorkBuddy, G2 card) in the browser pane.
- `docker build` OK; container imports the app.
### Still unverified
- Cloud deploy; real WorkBuddy run of desk_research/report_builder; Google Workspace actions.

## [2026-10-10 18:25 MYT] Backend live on Cloud Run
- First deploy failed: `.gcloudignore` pattern `workbuddy/` also excluded `backend/app/workbuddy` → `ModuleNotFoundError`. Fixed by anchoring patterns (`/workbuddy/`). Lesson: check `gcloud meta list-files-for-upload` before deploying.
- Live: https://startupbuddy-api-960127792850.asia-southeast1.run.app. `/health` ok + DB ok; `/mcp` lists 8 tools with the cloud key.
- Cloud smoke test (sim worker over cloud /mcp): "bubble tea kiosk near UNIMAS, Kota Samarahan" reached G1 with Places (10 competitors) and Gemini working under the Cloud Run service account. Test session deleted.

## [2026-10-10 18:55 MYT] UI: Serene Executive Slate design applied
- Owner added `DESIGN.md`, logo and banner (in `../pitch-and-design/`). Copied to `docs/DESIGN.md`, `docs/brand/`, `frontend/public/logo.png` (also the favicon).
- Frontend restyled: Manrope, navy/slate tokens, light-only; landing hero mirrors the banner (headline + 01–04 ladder, last rung navy); navy problem node, dashed WorkBuddy node; top bar fits phone width (verified no horizontal overflow).
- README shows the banner, live URLs, run/deploy commands and the team.

## [2026-10-10 19:30 MYT] Animated landing page (anime.js 4.5.0)
- Sections: hero (word-split headline, staged ladder, orbit of 16 agent dots, sample-run ticker), problem (count-up stats + 6-step "what happens today" story with a drawn line), workflow (drawn pipeline, 2-5-2 BMC waves, 5 council seats, G1/G2 chips), harness (6 guardrail cards), architecture (13-node click-to-explain SVG graph, edges draw in, packets flow along MCP/queue/agent paths), closing CTA, footer.
- Honest labels: hybrid search shown as "full-text today, vector next"; statuses per node (Built / tested / pending).
- Motion triggers via IntersectionObserver (content never stuck hidden); `prefers-reduced-motion` skips all animation; no horizontal overflow at phone width (graph scrolls inside its box).

## [2026-10-10 19:50 MYT] Landing: glass navbar + reversible scroll reveal
- Navbar (landing only, `TopBar glass`): transparent at the top; frosted glass (blur 16px, 62% white, soft border/shadow) once scrolled >12 px; stays pinned; restores at the top.
- Fixed sticky bug: `#root` had `height: 100%`, so the sticky header left with its 1-viewport container; now `min-height`.
- Reversible reveal (`.rv` + IntersectionObserver): elements fade/slide in when entering from below; hide again when they leave through the bottom (scrolling up). Card entrances moved from one-time anime.js to this; count-ups, line drawing, wave dots and the architecture graph stay one-time anime.js effects. Reduced motion shows everything statically.
- Floating navbar: when scrolled it detaches (top 12 px desktop / 8 px phone), insets to the content width, rounds to 18/14 px, 78% white glass + shadow; restores flush at the top. Verified no page-flow shift.
