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

## [2026-10-10 20:45 MYT] First real WorkBuddy end-to-end run: PASS (EXP-3)
### Verified (owner, WorkBuddy 5.7.6, cloud backend)
- One prompt in WorkBuddy ("Use StartupBuddy: I want to sell kolo mee near Padungan, Kuching") → `start_session` → app link → worker loop.
- desk_research: 11 findings (10 sourced, 1 estimated) + 6 regulations, first attempt. report_builder: 15.4k-char report + local DOCX. G1 and G2 relayed through WorkBuddy. Council verdict GO, 43 evidence items. ~77 credits for the whole run.
- G2 actions → `exec_failed: Google account not linked` (expected; token not set up yet).
### Issue
- WorkBuddy showed "工具「Skill」渲染失败" (its UI failed to render a Skill tool card) while hopping tencent-docx → minimax-docx → a C# script to build the DOCX: slow and credit-heavy.
### Fix
- Backend renders the DOCX from `report_markdown` (python-docx; strips lone surrogates/control chars found in the real report) and attaches it as an artifact; report-builder skill v0.3 forbids file creation/other doc skills. Tested on the real report: 44 KB, 122 paragraphs, 8 tables.
- `POST /sessions/{id}/report/docx` re-renders from the latest WorkBuddy result (backfill); `POST /sessions/{id}/actions/{aid}/retry` re-runs approved-but-failed actions (Retry button in the Advisor inspector).
- `backend/scripts/link_google.py` creates the Google token (Calendar + Gmail compose) for Secret Manager `gws-token`.

## [2026-10-10 22:40 MYT] UX upgrade: Studio feed, progressive canvas, Always allow, pilot summary
### What changed
- Backend: Gemini thought summaries (`include_thoughts`) streamed as `thinking` events; humanised emoji messages for phases, tools and agents; Session Assistant chat (`POST /sessions/{id}/chat`, MCP `ask_session`) grounded in the session context; "Always allow" per checkpoint (`auto_g1/auto_g2`, `POST /sessions/{id}/settings`, `always` on gate decisions; auto-approvals logged in the feed); pilot summary one-liner at the end; one retry per BMC block; search_knowledge capped at 2 calls; idempotent `ALTER TABLE` migrations at startup.
- Frontend: three panes. Left "Studio": chat + live feed (agent tags, data-source chips, collapsible thinking, suggestions, composer). Center: stepper (Ground→Build→Challenge→Act→Pilot), pilot-summary banner, canvas where agent cards appear only when reached (pop-in, skeleton bones, blueprint robots, blueprint grid, animated handoffs, 0.375rem status chips Verified/Sourced/Refinement flag), inspection drawer. Right "Decisions": checkpoint cards with Approve / Always allow, Autopilot switches, 5-seat council scorecards, first-steps checklist with Retry, report + DOCX.
### Verified (local, sim worker)
- Auto-approved full run (277 s): 55 thinking events, pilot summary produced; chat reply in ~10 s with labelled figures.
- Live UI: only reached nodes render; wave-1 skeletons + live thinking visible; G1 Approve from the new card.
### Still open
- Knowledge base nearly empty ("Found 0 references"): fill with verified MY/Sarawak sources next.


## [2026-10-11 02:30 MYT] Guardrails, business-type awareness, rational actions with follow-ups
### Why (owner report)
- "I want to sell drugs" was planned as a pharmacy; every action became a Google Meet even for F&B meet-ups; Google Maps scouting ran for every idea, digital ones included.
### What changed
- Phase 0 `intake_screener` (ScreenOut) with Malaysian law knowledge; verdicts allowed / regulated / ambiguous / prohibited; G0 clarification gate (never auto, ≤2 rounds); `blocked` phase with legal alternatives. Code backstops: RISK words → clarify; ILLEGAL words → block (law cited); deterministic fallback + one retry when the model stalls (it stalled on "ganja" content).
- business_type physical / digital / hybrid: Places scouting only when `needs_location_scouting`; digital ideas get online-competitor desk research; `screening` injected into every agent's context; prompts demand critical, evidence-backed judgement.
- Advisor kinds: email_outreach (draft → reply watcher → calendar on reply, Meet only if online, no attendees), site_visit (calendar, no Meet → Done/Reschedule), online_meeting, task. Follow-up watcher every 120 s + `POST /followups/check` + MCP `check_followups`; `POST /actions/{id}/followup` for founder updates. `gmail.readonly` added to link_google.py; without it the app shows "reconnect Google".
- Frontend: Intake Screener node (shield), G0 card, intake card (type, verdict, licences, red flags), blocked card + banner, kind icons, follow-up chips, Check replies, Done/Reschedule.
### Verified (local, 2026-10-11)
- "sell drugs" → G0 question (pharmacy or other?); answer "ganja and pills" → blocked (Dangerous Drugs Act 1952, Poisons Act 1952) with legal alternatives.
- "sell drugs" + "registered pharmacist, community pharmacy" → regulated, physical, licences: Type A licence (Poisons Act 1952), APC, council premises licence.
- "budgeting app for university students" → digital, no Maps calls (0), online competitor hints (MAE, Planner Bee, Spendee…), critical concerns (churn, low willingness to pay).
- Kolo mee → actions: 2 site visits (no Meet), 1 email outreach (JAIS), 1 task; executed: site visit → calendar (awaiting_update), email → Gmail draft (waiting_reply), task → checklist; Done update recorded.
- Reply parser: in-person reply → no Meet + location; "Google Meet call" → online; "see our website" → no event, next step only.
### Still open
- Reply watching live needs the owner to re-link Google with gmail.readonly and update the `gws-token` secret.


## [2026-10-13] Founder-in-the-loop block refinement (@-mention + council re-assessment)
### Why (owner request)
- The founder should be able to select a canvas block, type `@Block` in the Studio box with their preference, and have the agent refine it, re-score it and keep everything in sync: re-score only before G2, a full council round again after G2.
### What changed
- `app/agent/refine.py`:
  - `request()` validates and starts the work in the background; `_refine()` runs rewrite → re-assess → sync.
  - The block's own agent gets `REFINE` + `RefinedBlockOut` (with `change_note`); each version is a new `bmc_block` row (v1, v2, …).
  - Before G2: the 5 seats re-score only that block (`RESCORE` + `BlockRescoreOut`), then a new council round and verdict computed by `aggregate()`.
  - After G2: `_phase_council(rnd, trigger, set_phase=False)` runs a full round; a seat that fails keeps its previous review. Then the pilot summary is regenerated.
- Sync:
  - dependent blocks get `stale_reason` ("Re-check");
  - actions from the refined block are flagged `outdated`;
  - the report is updated: a still-queued `report_builder` task is rewritten, otherwise a new one is queued; when WorkBuddy is offline the backend renders the DOCX itself;
  - the feed shows the score change (`4.2 → 2.2 (-2.0) · verdict stays REVISE`) and the chat gets a reply.
- Bounds:
  - one refinement per session at a time;
  - at most 6 versions per block;
  - G2 can't be approved while a refinement is running;
  - illegal wishes are refused by the `ILLEGAL` backstop.
- API, MCP and schema:
  - `POST /sessions/{id}/blocks/{key}/refine`; chat and MCP `ask_session` route messages starting with `@Block`;
  - new MCP tool `refine_block`; `get_session_status` now returns `refining`, `council_verdict` and `block_scores`;
  - `session_detail` adds block version, history, change_note and stale_reason, the latest council round per seat, verdict round, trigger and previous means, `refining`, `refinable`, `actions[].outdated`; newest DOCX first;
  - migrations: `bmc_block.instruction`, `change_note` and `stale_reason`; `council_verdict.trigger`.
- Frontend:
  - `@` autocomplete in the Studio composer (score, version and "needs work" per block) and a block chip;
  - "✏️ Refine <block>" suggestions for flagged blocks; "Refine with my input" in the block inspector, with score, change and version history;
  - canvas chips (▲/▼ delta, `vN · your input`, Re-check); council seats animate while re-scoring;
  - scorecards show the round and trigger; actions show "Plan changed".
- Docs and skill: MCP_CONTRACT, AGENTS, README; worker skill v0.5.0 (`refine_block`).
### Verified (local, 2026-10-11/12)
- Guardrails:
  - "sell ganja noodles" → 422 citing the Dangerous Drugs Act 1952;
  - a second refinement while one is running → "One change at a time".
- Pre-G2 (session at gate_g2):
  - Revenue Streams + "RM7 student set meal and weekday breakfast combo" → v2 with change_note;
  - the 5 seats re-scored it 4.2 → 2.2 because a breakfast shift conflicts with the late-night positioning (an honest drop, not a rubber stamp);
  - verdict round 1, Cost Structure flagged Re-check, the action from Cost Structure flagged, DOCX re-rendered (WorkBuddy offline locally).
- Post-G2 (session done):
  - "@Key Partners add TEKUN Nasional and a local noodle supplier" → full council round 1, Key Partners 3.0 → 3.2;
  - the Mentor timed out and kept its previous review (labelled in the feed);
  - pilot summary regenerated, DOCX re-rendered.
- Frontend: `tsc` and `vite build` clean. A visual check in the browser is still pending: Docker needed a reset.
### Still open
- Dependent blocks are flagged, not rewritten automatically (by design, to keep cost down); the founder refines them with one tap.
- Not deployed yet: backend and frontend both need a redeploy (`infra/deploy-backend.ps1`, `infra/deploy-frontend.ps1`), and WorkBuddy needs worker skill v0.5.0.
