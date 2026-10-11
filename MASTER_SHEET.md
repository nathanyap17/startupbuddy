# MASTER_SHEET.md: StartupBuddy Project Master Sheet

> **Purpose.** The single, authoritative answer sheet for the Dormathon 2026 Track 2 judging criteria (Problem relevance, Agentic capability, WorkBuddy integration depth, Output reliability, Live execution), plus feasibility and the business model. Every figure is sourced or traced to the code or a recorded run. Each section opens with a plain-language summary; what is proven, assumed or not yet verified is stated explicitly.
>
> **Project:** StartupBuddy - An agentic AI solution that takes aspiring Malaysian founders from a vague business idea to a locally validated, council-reviewed business model and their first booked stakeholder meetings, powered by Tencent WorkBuddy.
> **Tagline:** From idea to first meeting.
> **Team:** SMILING FACE WITH SUNGLASSES: Nathan Yap (leader), Abraham Pang, Malcolm Sim, Zoe Tan
> **Event:** Dormathon 2026, Track 2: WorkBuddy Agentic Solutions, 10–11 October 2026 (3-min pitch + 2-min Q&A)
> **Try it:** https://dormathon-workspace-1.web.app · API: https://startupbuddy-api-960127792850.asia-southeast1.run.app · Code: https://github.com/nathanyap17/startupbuddy
> **Status date:** 2026-10-11 (live on Google Cloud Run + Firebase Hosting; latest build with intake guardrails and follow-ups deployed; repository in sync with GitHub, 19 commits)

### How to read the evidence labels

| Label | Meaning |
|---|---|
| **[n]** | Published source; see the reference list at the end |
| **(Built)** | Verified in the working system: code, a recorded run, or the live deployment |
| **(Design)** | A design choice or engineering assumption, not an empirical finding |
| **(Pending)** | Stated in good faith but not yet verified; listed in section 8 |
| **Roadmap** | Planned, not built. Never presented as working |

---

## Executive summary

**In plain words:** Many young Malaysians want to start a business but stall at a vague idea: few graduates become entrepreneurs, young people say they don't know where to get help, and formal finance rarely reaches them. StartupBuddy takes one sentence, for example "I want to sell kolo mee near Padungan, Kuching", typed into Tencent WorkBuddy or the web app. It checks the idea against Malaysian law, grounds it in the founder's real neighbourhood, has 16 AI agents build and challenge a full business model, and, only after the founder approves, puts the first site visits in their calendar and drafts their first outreach emails. WorkBuddy does real work in the loop: it starts the run, researches the market, writes the report and relays the founder's decisions. It is live today; the next step is a pilot with one campus cohort.

| Criterion (Track 2 rubric) | One-line answer |
|---|---|
| 1. Problem relevance & real-world utility | Aspiring founders lack locally grounded validation and a path to the right people; one session replaces weeks of scattered searching (≈ 4–5 min per full run in our tests) (Built) |
| 2. Autonomous workflow & agentic capability | Intake screener → coordinator → 9 canvas agents in 3 dependent waves → 5-seat council in parallel → advisor; retries, fallbacks and three human checkpoints (Built) |
| 3. WorkBuddy integration depth | WorkBuddy connects as a custom MCP connector, starts the run from one prompt, pulls tasks from a queue (desk research, report), relays G0/G1/G2 decisions and answers questions (Built) |
| 4. Output reliability, validation & verification | Every figure labelled sourced / estimated / needs verification (enforced in code and database); council QC aggregated by code; illegal ideas blocked; DOCX report + real Calendar/Gmail outputs (Built) |
| 5. Live execution, prototype & pitch | One prompt in WorkBuddy → end-to-end run on the deployed app, recorded on 2026-10-10/11 (Built); live demo available at the event |

---

## 1. Problem relevance and real-world utility

> **In plain words:** Malaysian business is mostly micro-business, and young people rarely make the jump. The tools they find are generic, help is scattered across agencies, and nothing helps them take the first real step.

### 1.1 Context: who is affected, and where
- MSMEs are 96.2 % of Malaysian establishments (1,292,580), and microenterprises are 77.4 % of MSMEs (2025) [1].
- About 1.4 % of 48,709 public-university graduates were self-employed in the 2010 tracer study [2], and 1.7 % in 2013 against a 5 % government aspiration [3]. (Pending: latest tracer study.)
- Primary user: a final-year student or fresh graduate (e.g. in Kuching) with an idea and no network (Design). *Aisyah*, used in the pitch, is an illustrative persona.

### 1.2 The burden
| Measure | Value |
|---|---|
| Youths unaware where to seek advice or financial aid | Reported by the 2023 RYSE survey [4] (Pending: primary report) |
| Youth entrepreneurs financed by financial institutions | 6 % (KRI, cited in [5]) (Pending: KRI original) |
| New SMEs failing within 5 years | "60 %", a commonly cited estimate with weak sourcing [6]; not used in the pitch |

### 1.3 The gaps (why current practice fails)
1. Generic AI validators and plan generators do not use the founder's actual street, competitors or Malaysian licensing [10].
2. MYStartup Single Window aggregates resources and connections [7] but does not analyse an idea or act on it.
3. Nothing turns a plan into a first meeting with the founder's consent.

### 1.4 Real-world utility (what a session delivers)
| Before | With StartupBuddy (recorded runs, 2026-10-10/11) |
|---|---|
| Guessing the market | 8 kolo mee stalls within 1 km of Jalan Padungan found via Google Places (Built) |
| Generic plans | A 9-block canvas tied to the place, reviewed by 5 seats (Built) |
| Not knowing which rules apply | Licences named up front, e.g. MBKS food premises licence, food handler training, typhoid vaccination (Built) |
| No first step | Calendar site visits, Gmail drafts and checklist tasks, created after approval (Built) |
| Weeks of searching | ≈ 4–5 min per full run (202 s and 277 s measured locally with both checkpoints auto-approved) (Built) |

## 2. Autonomous workflow and agentic capability

> **In plain words:** One goal goes in; agents understand it, split the work, run in parallel where they can, check each other and fix what fails. The founder only steps in at checkpoints.

### 2.1 Pipeline (Built)
| Phase | Agents | Tools | Checkpoint |
|---|---|---|---|
| 0 · Intake | Intake Screener | Malaysian law knowledge + code backstops | **G0** clarification, only if ambiguous; never auto-approved |
| 1 · Ground | Problem Coordinator | Google Places (physical/hybrid only), knowledge search, WorkBuddy desk research | **G1** confirm or edit the problem |
| 2 · Build | 9 BMC agents in waves ① 2 → ② 5 → ③ 2 | knowledge search | |
| 3 · Challenge | 5 council seats in parallel (Customer, CEO, Investor, CFO, Local Mentor) | deterministic aggregation in code | |
| 3b · Report | Tencent WorkBuddy | report skill; backend renders DOCX | |
| 4 · Act | Advisor | Google Calendar, Meet, Gmail drafts | **G2** approve each action (or opt-in Always allow) |
| 5 · Follow up | Follow-up reader | Gmail read-only, Calendar | consent given at G2 |

**16 agents** do the core work (1 coordinator + 9 BMC + 5 council + 1 advisor); helper agents handle intake screening, reply reading, chat and the pilot summary. All run on Gemini 3.5 Flash via Google ADK 2.6.1 with structured (Pydantic) outputs (Built).

### 2.2 Rubric capabilities
| Capability | Evidence |
|---|---|
| Task decomposition | Intake screener classifies verdict, business type and licences; coordinator decomposes into who / where / pain / demand / competition (Built) |
| Multi-step planning | 5 phases with 3 checkpoints; phase state persisted in Postgres (Built) |
| Parallel execution | Wave 2 runs 5 agents at once; the council runs 5 seats at once (`asyncio.gather`) (Built) |
| Multi-agent collaboration | Each wave reads earlier blocks; the council reads the whole canvas; the advisor cites the agent each action came from (Built) |
| Dynamic error handling | Per-turn timeouts; one automatic retry per canvas block; screener retry then deterministic fallback; WorkBuddy task leases, deadlines and max 2 attempts; visible fallbacks (Built) |
| Adapts to the idea | Physical vs digital: a digital budgeting app made 0 Google Maps calls and researched online competitors instead (Built, local test 2026-10-11) |

## 3. WorkBuddy integration depth

> **In plain words:** WorkBuddy is where the founder starts and talks, and it does real work (research, the report, relaying decisions), not just chat.

- **Connection:** StartupBuddy's MCP server (streamable HTTP, `X-API-Key`, 10 tools) is added in WorkBuddy's MCP Server Management (`mcp.json`); verified with WorkBuddy 5.7.6 (EXP-1, Built) [8][9].
- **Task queue:** MCP lets WorkBuddy call us but not the reverse, so cloud agents enqueue tasks and WorkBuddy's `startupbuddy-worker` skill long-polls `await_next_task` (≤ 25 s per call, under WorkBuddy's ~30 s tool limit); EXP-2 passed with 10 polls and 3 tasks (Built).
- **Real work done by WorkBuddy in the recorded run:** started the session from one prompt; `desk_research` returned 11 findings (10 sourced) and 6 regulations; `report_builder` wrote a 15.4k-character report; relayed G1/G2 decisions (Built).
- **Skills:** worker (session start, task loop, G0/G1/G2 relay, `ask_session`, `check_followups`), desk research, report builder (Built).
- **Honest boundary:** the 16 agents run on Google Cloud Run; WorkBuddy is the entry point, researcher, writer and decision relay. Roadmap: WorkBuddy executes the approved Google actions through its own connectors.

## 4. Output reliability, validation and verification

> **In plain words:** You can check every number, wrong or illegal ideas are caught early, and what you get is complete and usable: a report, calendar entries and email drafts.

| Check | What it does |
|---|---|
| Evidence labels | Every figure is `sourced` (needs a URL), `estimated` (needs a method) or `needs_verification`; unsupported labels are downgraded in code and the database rejects violations (Built) |
| Intake guardrails | "Sell drugs" → G0 clarification; "ganja and pills" → blocked, citing the Dangerous Drugs Act 1952 and Poisons Act 1952; "registered pharmacist, community pharmacy" → regulated with Type A licence (Poisons Act 1952), APC and premises licence (Built, local tests 2026-10-11) |
| Code backstops | Risky words force clarification even if the model says "allowed"; clearly illegal words block with the law cited; deterministic fallback when the model stalls (Built) |
| Council QC | 5 seats score all 9 blocks; plain code computes per-block means and the majority verdict; weak blocks get a "Refinement flag" (Built) |
| Right action, safely | Email outreach first (Gmail **draft**, never sent), site visits without video links, online meetings only when naturally online, tasks as checklist items; follow-up events go into the founder's own calendar with no attendees (Built) |
| Deliverables | Problem statement + labelled evidence, 9-block canvas, 5 scorecards, pilot summary, Markdown report + DOCX (44 KB, 8 tables in the recorded run), Calendar events, Gmail drafts (Built) |
| Audit trail | Every thought summary, tool call, handoff and latency is stored and streamed live to the canvas (Built) |

## 5. Live execution and prototype

> **In plain words:** It's deployed and it runs end to end from one prompt; the demo is a real run, not a mock.

| Item | Status |
|---|---|
| Backend: FastAPI + ADK on Cloud Run (`asia-southeast1`), Cloud SQL Postgres, Secret Manager | Live; `/health` ok + db ok (Built, 2026-10-11) |
| Frontend: landing (anime.js), Studio chat feed, live canvas, decisions pane, report | Live on Firebase Hosting (Built) |
| One prompt in WorkBuddy → end-to-end run → Calendar + Gmail | Recorded end to end (Built, 2026-10-10/11) |
| Demo assets | 29 s screen-recording cut of the real run; 30 s animated walkthrough (labelled as such) with voice-over (Built) |
| Code size | ≈ 2.8k lines of backend Python, ≈ 1.4k lines of frontend TypeScript (measured 2026-10-11) |

## 6. Feasibility

> **In plain words:** It already runs on mainstream cloud services at small cost per session; what remains is content (the knowledge base) and a pilot.

### 6.1 Proven vs not proven
| Component | Status |
|---|---|
| Deployment, WorkBuddy connector, task queue, real end-to-end run | Proven (Built) |
| Google Calendar events and Gmail drafts after approval | Proven on the demo account (Built) |
| Intake guardrails, physical vs digital adaptation | Proven in local tests (Built) |
| Reply tracking (Gmail read-only) | Reply parser proven on sample replies (in-person, online, no-time); live tracking needs the read-only permission on the deployed token (Pending) |
| Verified Malaysian knowledge base | 1 document today (Pending) |
| Automated test suite | None yet; verification has been end-to-end runs and logged experiments (Pending) |

### 6.2 Risks and mitigations
| Risk | Likelihood | Mitigation |
|---|---|---|
| WorkBuddy offline during a run | Medium | Task deadlines + labelled fallback; the run completes without it |
| Model stalls or returns invalid output | Medium | Timeouts, one retry, deterministic fallbacks, structured outputs |
| Hallucinated figures | Medium | Evidence labels enforced in code; council review; founder checkpoints |
| Credit cost of WorkBuddy polling | Medium | Worker stops after 20 idle polls (≈ 1.4 credits per poll measured); report DOCX moved server-side |
| Legal misreading | Low–medium | Intake screener + code backstops; "guidance, not legal advice" |

### 6.3 Roadmap
| Phase | Milestones |
|---|---|
| Next 2 weeks | Grow the verified knowledge base (SSM, DBKU/MBKS, food handler, TEKUN, SME Corp, MYStartup, halal, OpenDOSM); enable live reply tracking; add automated tests |
| Pilot (one campus cohort) | Measure time to first meeting, % figures sourced, meetings held within 30 days, cost per session |
| After the pilot | Vector search (hybrid retrieval), council revision loop, WorkBuddy-executed Google actions, multi-user accounts |

## 7. Business model

> **In plain words:** Students use it free; universities, incubators and state programmes pay because their founders arrive prepared.

| Segment | Role | Value proposition |
|---|---|---|
| Students and first-time founders | User | A grounded plan and first meetings in one session, free |
| Universities, incubators, state entrepreneurship programmes | Payer (target) | Founders who arrive validated, with a reviewed plan and evidence |
| Lecturers, mentors, programme officers | Influencer | Less time on first-draft reviews |

**Pricing method (no price quoted yet):** `price per session ≈ (Gemini + cloud + WorkBuddy cost) × (1 + margin)`, sold per cohort licence. One full WorkBuddy run used ≈ 77 credits before the report step was optimised; Gemini and Cloud Run cost per session will be measured in the pilot.

**Market:** 1,292,580 MSMEs in Malaysia [1]. **Ask:** a pilot with one Sarawak campus cohort.

> **Status:** proposed; no customer or partner is signed. All payers are targets.

## 8. Limitations and open verification items

| # | Item | Current state | Action needed |
|---|---|---|---|
| 1 | Knowledge base | 1 verified document | Add ≥ 10 verified Malaysian/Sarawak sources |
| 2 | Live reply tracking | Parser tested; deployed token may lack Gmail read-only | Re-link Google with read-only scope, update `gws-token`, test a real reply |
| 3 | Automated tests | None | Add pytest for queue, guardrails, evidence labels |
| 4 | Tracer-study figures | 2010/2013 | Find the latest MOHE tracer study |
| 5 | RYSE and KRI figures | Secondary reports | Read the primary reports |
| 6 | 60 % failure rate | Weak sourcing | Not used in the pitch |
| 7 | Competitor features | Vendor pages | Hands-on check |
| 8 | Run time "≈ 4–5 min" | Local runs with auto-approval | Measure on the deployed stack during the pilot |
| 9 | WorkBuddy depth | Agents run on Cloud Run | Move approved Google actions to WorkBuddy connectors |

## 9. Glossary

| Term | Plain meaning |
|---|---|
| Agent | An AI component with one job and specific tools |
| Business Model Canvas (BMC) | A one-page, 9-block description of how a business works |
| Checkpoint (G0/G1/G2) | A point where the founder must answer or approve before the agents continue |
| Council | Five simulated reviewers (Customer, CEO, Investor, CFO, Local Mentor) who score the canvas |
| MCP | Model Context Protocol: a standard way for AI apps like WorkBuddy to call external tools |
| Task queue | A list of jobs the cloud agents leave for WorkBuddy to pick up |
| Evidence label | Sourced / estimated / needs verification, attached to every figure |
| WorkBuddy | Tencent's desktop AI agent; mandatory for this track |

## References

1. SME Corporation Malaysia. (2025). *Profile of MSMEs 2015–2025.* https://smecorp.gov.my/index.php/en/policies/2020-02-11-08-01-24/profile-and-importance-to-the-economy
2. International Journal of Business and Society, UNIMAS. *Graduate entrepreneurship in Malaysia.* https://www.ijbs.unimas.my/repository/pdf/Vol15No1paper4.pdf
3. HRMARS. *The relationship between intention and actual entrepreneurial as a career choice of Malaysian graduates.* https://hrmars.com/papers_submitted/6075/The_Relationship_between_Intention_and_Actual_Entrepreneurial_As_A_Career_Choice_of_Malaysian_Graduate.pdf
4. Malay Mail. (2023, October 25). *Survey: Malaysian youths' limited attraction to entrepreneurship calls for greater outreach, mentorship programme.* https://www.malaymail.com/news/malaysia/2023/10/25/survey-malaysian-youths-limited-attraction-to-entrepreneurship-calls-for-greater-outreach-mentorship-programme/98321
5. IIUM Repository. *Youth entrepreneurs and access to financing.* https://irep.iium.edu.my/81474/
6. ASEAN Entrepreneurship Journal, 6(1), UiTM. https://ir.uitm.edu.my/43932/1/43932.pdf
7. Vulcan Post. *MYStartup Single Window.* https://vulcanpost.com/859816/mystartup-single-window-startup-ecosystem-platform-malaysia
8. Tencent Cloud. *WorkBuddy Enterprise: Connector management.* https://cloud.tencent.com/document/product/1831/134453
9. WorkBuddy. *Connector developer documentation.* https://open.workbuddy.cn/docs/connector
10. Preuve AI. *Alternatives to ValidatorAI / IdeaBuddy* (vendor comparison pages). https://preuve.ai/compare/alternatives-to/validatorai

*References checked via search summaries on 2026-10-10 (full text not yet read for 2–6). (Built) claims were checked on 2026-10-11 against the live deployment (`/health`, routes), the repository (`backend/app`, `frontend/src`, 19 commits in sync with GitHub), `docs/BUILD_LOG.md` and the recorded demo runs.*
