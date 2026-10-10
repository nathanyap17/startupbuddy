# PLAN.md: StartupBuddy Development Plan

> **Context:** Dormathon, Track 2 (WorkBuddy Agentic Solutions). Judged on: real problem and user value · agentic workflow · meaningful use of WorkBuddy · end-to-end execution from one prompt · usable, verifiable results. Core question: *can the agent use WorkBuddy to solve a real problem and actually get things done?*
> **Event:** Dormathon, 10–11 Oct 2026. **Submission deadline: 2026-10-11 09:30 MYT** (UTC+8).
> **Submission items (owner, 2026-10-10):** project repo link (https://github.com/nathanyap17/startupbuddy) · landing page link (`https://dormathon-workspace-1.web.app`) · slide deck · documentation. Extra: **30-second software demo video** (screen recording of the product).
> **Presentation:** 5 minutes = **3 min pitch + 2 min Q&A**. Deck (`../pitch-and-design/DECK.md`) and pitch script (`../pitch-and-design/PITCH.md`) are written as a pair, page for page, copying facts only from `MASTER_SHEET.md`. **WorkBuddy is mandatory for slides and documentation:** produce the deck file and the documentation inside WorkBuddy, from these .md sources.
> **Approach:** ship a **first pilot** by the deadline (scope below), then refine over time; every refinement is logged in `docs/BUILD_LOG.md`.

---

## ✅ HOLD lifted 2026-10-10 15:45 MYT (owner approved docs)

Owner runs every push and deploy; Claude prepares the exact command. Throwaway experiment services (`exp-*`) are deleted after use.

---

## Pilot scope (deadline 2026-10-11 09:30 MYT, ≈18 h from 2026-10-10 15:30)

| Keep in pilot | Moved to post-pilot refinement |
|---|---|
| All 16 agents (prompted ADK agents; waves + parallel council) | Council → BMC revision loop (pilot: single pass; council shows "revise" notes) |
| Live canvas (SSE) + landing page | EmbeddingGemma (pilot: Vertex embeddings or full-text only over a small KB) |
| WorkBuddy MCP queue with `desk_research` + `report_builder` skills | `financial_sheet`, `one_pager` skills |
| Google Places competitors + evidence labels | OpenDOSM live lookup (pilot: a few seeded, sourced figures) |
| Gates G1 + G2; Advisor creates a **Calendar event with Meet link** (reuse PepperDex calendar MCP code), + Gmail draft if time | Drive folder action |
| Seeded complete demo session (fallback for the live run) | Knowledge base ≥30 docs (pilot: ~10 verified docs) |

### Pilot timeline (MYT, guide)
| When | What | Who |
|---|---|---|
| 10 Oct 15:30–16:30 | Push docs · enable APIs · create Cloud SQL (runs in background) · deploy EXP-1 echo MCP · connect WorkBuddy | Nathan runs, Claude prepares |
| 16:30–21:00 | Backend: DB models, queue + MCP tools, agents, Places tool, SSE | Claude |
| 21:00–00:30 | Frontend: landing + sessions + canvas + gates + report | Claude |
| 00:30–02:30 | Deploy Cloud Run + Firebase; WorkBuddy end-to-end run; seed demo session | Nathan + Claude |
| 02:30–05:00 | MASTER_SHEET update → DECK.md + PITCH.md → deck file and docs produced **in WorkBuddy**; evidence primary sources | Team + Claude |
| 05:00–08:30 | Rehearse 3-min pitch, Q&A prep, record 30 s demo video, buffer | Team |
| **11 Oct 09:30** | **Submit:** repo link · landing link · deck · documentation | Nathan |

## Decisions already made (so they aren't re-litigated)

| Topic | Decision (date) |
|---|---|
| Project folder | `startupbuddy/` inside `dormathon-workspace/`, Pepperdex-style layout: `adk-docs/`, `adk-python/`, `sandbox/` and `pitch-and-design/` sit beside it (2026-10-10) |
| Frontend | One React + Vite app in `frontend/`: landing page at `/`, web app at `/app`. One Firebase Hosting site (2026-10-10) |
| Auth | **Demo account only.** No registration and no login on the web app. One seeded `demo_user`. The MCP endpoint is protected by an API key (WorkBuddy requires an auth method) (2026-10-10) |
| WorkBuddy integration | **Task-queue pattern.** ADK agents enqueue `workbuddy_task`. WorkBuddy's `startupbuddy-worker` skill long-polls `await_next_task` over our MCP connector, runs the named skill and submits the result. Direct server→WorkBuddy calls are impossible over MCP (WorkBuddy is the client) (2026-10-10) |
| Agent roster | 16 agents: 1 ProblemCoordinator · 9 BMC (one per canvas block, 3 dependency waves) · 5 Council (Customer, CEO, Investor, CFO, Mentor) · 1 Advisor (Google Workspace MCP, approval-gated). Details in `docs/AGENTS.md` (2026-10-10) |
| Scope | Malaysia, including Sarawak (2026-10-10) |
| Region | `asia-southeast1` for Cloud Run, Cloud SQL and the bucket. Vertex model region per EXP-4 |
| GCP project | `dormathon-workspace-1` (account `demony11111@gmail.com`, corrected 2026-10-10). **Do not create another project.** Firebase attached 2026-10-10 (project number 960127792850). Billing linked |
| Public URL for WorkBuddy | Cloud Run URL directly. No `cloudflared` tunnel; Firebase Hosting serves only the frontend (2026-10-10) |
| Who conducts | WorkBuddy starts a run and executes skills; the ADK pipeline owns phase order and gates. Either entry point (WorkBuddy prompt or web "Start") works |
| Emails | Drafted, never auto-sent |

## Phases

### Phase A: Validate risky assumptions (`../sandbox/EXPERIMENTS.md`)
| Task | Reference | Exit condition |
|---|---|---|
| WorkBuddy custom connector reaches our MCP on Cloud Run | EXP-1 | WorkBuddy lists our tools and a call round-trips |
| Long-poll `await_next_task` under the tool timeout, in a loop | EXP-2 | 10 consecutive polls without WorkBuddy erroring or abandoning the loop |
| WorkBuddy skill runs a multi-step task and posts structured JSON back | EXP-3 | Result passes Pydantic validation 3/3 |
| Gemini model id + region on Vertex | EXP-4 | Model id pinned in `docs/CREDENTIALS.md` |
| Embedding backend | EXP-5 | Decision recorded (EmbeddingGemma vs Vertex) |
| Places API + OpenDOSM give usable local numbers for a kolo mee test case | EXP-6 | One evidence table generated from live data |
| Headless `cbc -p` on Cloud Run (option, not plan) | EXP-7 | Result recorded either way |

### Phase B: Skeleton
| Task | Exit condition |
|---|---|
| `docker-compose.yml` Postgres+pgvector, Alembic migrations from `docs/DATA_MODEL.md` | `alembic upgrade head` clean |
| FastAPI app: sessions, SSE `/sessions/{id}/events`, health | `pytest -q` green |
| MCP server `/mcp` with the tools in `docs/MCP_CONTRACT.md` + task queue | EXP-1/2 rerun against the real server |
| Vite app: landing + `/app` session list + empty canvas | Loads locally |

### Phase C: Agents
| Task | Exit condition |
|---|---|
| ProblemCoordinator + Places/OpenDOSM/RAG tools + gate G1 | Kolo mee test produces a problem statement with labelled evidence |
| 9 BMC agents in 3 waves, streaming `agent_event` | Canvas fills block by block |
| Council (5 parallel) + deterministic aggregation + ≤2 revision rounds | Verdict JSON with scores and revision log |
| Advisor + Google Workspace MCP + gate G2 | Approved actions create a Calendar event, a Gmail draft and a Drive folder on the demo account |
| WorkBuddy skills: desk research, report builder, financial sheet, one-pager | Each produces an artifact that is stored and linked in the web app |

### Phase D: Knowledge base
| Task | Exit condition |
|---|---|
| Curate `knowledge/` (SSM, SME Corp, MYStartup/Cradle, TEKUN, MARA, SDEC, Sarawak councils, BMC framework) with source URLs | ≥30 verified documents, each with URL + retrieval date |
| Ingest + hybrid search | Top-5 recall check on 20 hand-written queries |

### Phase E: Demo hardening and ship (behind the HOLD)
| Task | Exit condition |
|---|---|
| Seed one complete demo session (fallback if live run is slow) | Loads instantly |
| Cloud Run + Cloud SQL + Firebase deploy | Public URL works end to end with WorkBuddy pointed at the Run URL |
| `MASTER_SHEET.md` updated with (Built) evidence | Every claim labelled |
| `DECK.md` + `PITCH.md` (inter-linked: same slide numbers, timing map) | Pitch timing checked against slot length |
| Software demo video: storyboard → screen-record one live run (WorkBuddy + web canvas), seeded session as backup take | Video within length limit, shows WorkBuddy doing the work |

## Gates / holds
- G1 (in product): the user confirms the problem statement before BMC runs.
- G2 (in product): the user approves each Advisor action before any Google Workspace call.
- Project: no push or deploy without the owner's go-ahead in chat.

## Cut order (if time runs short)
1. Financial-model spreadsheet skill (keep the CFO numbers inside the report)
2. EmbeddingGemma (fall back to Vertex embeddings)
3. Council revision loop (single pass, still shown)
4. Drive folder action (keep Calendar + Gmail draft)

**Never cut:** one-prompt end-to-end run · WorkBuddy task queue doing real work · live canvas · council verdict with evidence labels · approval gate.

## Open items
1. ~~Dates, slot, deliverables~~: resolved 2026-10-10 (see header).
2. ~~Team~~: resolved 2026-10-10.
3. ~~Repo~~: `https://github.com/nathanyap17/startupbuddy` (2026-10-10).
4. ADK version: **pin `google-adk==2.6.1`** for the pilot (matches the `../adk-python` clone; no time to absorb API changes). Revisit after the pilot.
5. ~~WorkBuddy custom connectors~~: WorkBuddy has *MCP Server Management*, which edits `C:\Users\User\.workbuddy-ai\mcp.json` (screenshot `workbuddy/workbuddy-add-mcp.png`, 2026-10-10). The connection itself is still to be tested in EXP-1.
6. Evidence primary sources (E2–E4): Claude researches them in the 02:30–05:00 block.

## Task allocation
| Owner | Responsibility |
|---|---|
| Nathan Yap (leader) | Logins (gcloud, firebase, WorkBuddy), connector setup, deploys, pushes, demo, submission |
| Abraham Pang · Malcolm Sim · Zoe Tan | Team members (info only; owner assigns deck/pitch/video roles) |
| Claude | Code, docs, experiment scripts, deck/pitch drafts, exact commands for the owner |

**Team name:** SMILING FACE WITH SUNGLASSES.
