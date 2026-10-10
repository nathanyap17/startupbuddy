# MASTER_SHEET.md: StartupBuddy Project Master Sheet

> **Purpose.** The single, authoritative answer sheet for the Dormathon Track 2 judging criteria. Every figure is sourced or traced to the code. Each section opens with a plain-language summary, and what is proven, assumed or not yet verified is stated explicitly.
>
> **Project:** StartupBuddy - An agentic AI solution that takes aspiring Malaysian founders from a vague business idea to a locally validated, council-reviewed business model and their first booked stakeholder meetings, powered by Tencent WorkBuddy.
> **Tagline:** From idea to first meeting.
> **Team:** SMILING FACE WITH SUNGLASSES: Nathan Yap (leader), Abraham Pang, Malcolm Sim, Zoe Tan
> **Event:** Dormathon, Track 2: WorkBuddy Agentic Solutions, 10–11 October 2026 (submission 2026-10-11 09:30 MYT). Deliverables: repo, landing page, slide deck, documentation; 3-min pitch + 2-min Q&A; 30 s demo video
> **Try it:** https://dormathon-workspace-1.web.app (not deployed yet) · Code: https://github.com/nathanyap17/startupbuddy (not pushed yet)
> **Status date:** 2026-10-10 (pre-build: design and research only; **nothing below is Built yet**)

### How to read the evidence labels

| Label | Meaning |
|---|---|
| **[n]** | Published source; see the reference list at the end |
| **(Built)** | Verified in the working system: code, tests or the live deployment |
| **(Design)** | A design choice or engineering assumption, not an empirical finding |
| **(Pending)** | Stated in good faith but not yet verified; listed in section 7 |
| **Roadmap** | Planned, not built. Never presented as working |

---

## Executive summary

**In plain words:** Many young Malaysians want to start a business but stall at a vague idea. Few graduates become entrepreneurs, young people say they don't know where to get help, and formal finance rarely reaches them. StartupBuddy takes one sentence ("I want to sell kolo mee near Padungan") and runs 16 cooperating AI agents. They check the real neighbourhood, write a full Business Model Canvas, have a simulated customer, CEO, investor, CFO and mentor review it, and then, with the founder's approval, book the first meetings and prepare the documents. Tencent WorkBuddy does real work in the loop: research, reports, spreadsheets and the founder conversation. Status: designed, not yet built.

| Criterion | One-line answer |
|---|---|
| 1. Real problem & user value | Aspiring founders lack locally grounded validation and a path to the right people; value = time from idea to first booked meeting |
| 2. Agentic workflow | 16 agents: coordinator, 9 canvas agents in dependency waves, 5-seat council with bounded revision, advisor with approval gate (Design) |
| 3. Meaningful use of WorkBuddy | WorkBuddy starts runs, executes research/report/spreadsheet/one-pager skills from a task queue and relays approvals (Design) |
| 4. End-to-end execution | One prompt → problem → canvas → council → report → approved actions, no step-by-step guiding (Design) |
| 5. Usable, verifiable results | Every figure labelled sourced / estimated / needs-verification; real DOCX/XLSX/PPTX and real calendar/draft/Drive outputs (Design) |

---

## 1. Real problem and user value

> **In plain words:** Starting a business in Malaysia is mostly micro-business, and young people rarely make the jump. The tools they find are generic; the government portal lists resources but does not do the work with them.

### 1.1 Context
- MSMEs are 96.2% of Malaysian establishments (1,292,580), and microenterprises are 77.4% of MSMEs (2025) [1].
- About 1.4% of 48,709 public-university graduates were self-employed in the 2010 tracer study [2], and 1.7% in 2013 against a 5% government aspiration [3]. (Pending): latest tracer study.

### 1.2 The burden
| Measure | Value |
|---|---|
| Youths unaware where to seek advice or financial aid | Reported by 2023 RYSE survey [4] (Pending: primary report) |
| Youth entrepreneurs financed by financial institutions | 6% (KRI, cited in [5]) (Pending: KRI original) |
| New SMEs failing within 5 years | "60%", a commonly cited estimate with weak sourcing [6] |

### 1.3 The gaps
1. Generic AI validators and plan tools do not use the founder's actual neighbourhood (competitors, demographics, licensing) (Design, from competitor scan).
2. MYStartup Single Window aggregates resources, mentorship and funding information [7] but does not analyse an idea or act.
3. Nothing turns a plan into booked conversations with the founder's consent.

### 1.4 User and measurable value
Primary user: a final-year student or fresh graduate in Kuching with an idea and no network (Design).
| Indicator | Measured as (Roadmap) |
|---|---|
| Time to confirmed problem statement | minutes from session start to G1 approval |
| Time to reviewed canvas | minutes to council verdict |
| First action | approved calendar event / email draft created in session |
| Evidence quality | % of report figures labelled `sourced` |

## 2. Agentic workflow

> **In plain words:** Agents split the job, work in parallel where they can, check each other, and fix weak parts before anything reaches the user.

| Capability judged | How StartupBuddy does it (Design) |
|---|---|
| Task decomposition | Coordinator turns intent into who / where / pain / demand / competition sub-questions |
| Multi-step execution | 4 phases with two human gates (G1 problem, G2 actions) |
| Tool calling | Places, OpenDOSM, hybrid knowledge search, WorkBuddy task queue, Google Workspace MCP |
| Agent collaboration | 9 canvas agents read each other's blocks across 3 waves |
| Parallel workflows | Wave 2 runs 5 agents at once; council runs 5 seats at once |
| Validation & QC | Council scores aggregated by code; weak blocks revised (≤2 rounds); DB rejects unlabelled figures |
| Dynamic adaptation | Revision targets only flagged blocks; WorkBuddy timeouts trigger labelled fallbacks |

## 3. Meaningful use of WorkBuddy

> **In plain words:** WorkBuddy is the worker that produces the research and documents and the place the founder talks to. It is not a chat window bolted on.

- Our MCP server is added to WorkBuddy as a custom connector (URL, streamable HTTP, API-key header), a supported configuration [8][9].
- Because MCP lets WorkBuddy call us but not the reverse, agents enqueue tasks and WorkBuddy pulls them with a long-poll tool that answers within WorkBuddy's ~30 s tool limit [9] (Design).
- WorkBuddy skills: desk research, report builder (DOCX/PDF), financial sheet (XLSX), one-pager (PPTX/PDF), plus a worker skill that starts sessions and relays gates (Design).

## 4. End-to-end execution

> **In plain words:** One sentence in WorkBuddy or the web app runs the whole thing; the user only answers two yes/no style checkpoints.

Flow (Design): intent → Phase 1 problem + evidence → G1 → 9-block canvas → council → revisions → report, spreadsheet, one-pager → advisor actions → G2 → Calendar/Meet event, Gmail draft, Drive folder.

## 5. Usable and verifiable results

> **In plain words:** You can check every number, and you get real files and real calendar entries, not only a chat answer.

| Output | Verifiability |
|---|---|
| Problem statement with evidence table | each row labelled; `sourced` rows carry URLs (Design, DB constraint) |
| Business Model Canvas (9 blocks) | assumptions listed per block |
| Council verdict | per-seat scores, must-verify list, deterministic aggregation |
| Report / XLSX / one-pager | stored artifacts linked in the app |
| Actions | external ids recorded (event id, draft id, folder id) |

## 6. Feasibility and business model (supporting)

| Factor | Situation |
|---|---|
| Stack | React, FastAPI, Postgres+pgvector, Google ADK, Vertex Gemini, Cloud Run, Firebase (Design) |
| Prior experience | Team built a similar ADK + MCP + Cloud Run system (PepperDex) (Design; internal) |
| Main risks | WorkBuddy connector behaviour (EXP-1/2), model availability (EXP-4), live-demo latency (seeded fallback) |

Business model (Roadmap): free for students via universities and incubators (influencers/payers), paid tier for programme operators to pre-screen applicants. All partners are **targets**; nothing is signed.

## 7. Limitations and open verification items

| # | Item | Current state | Action needed |
|---|---|---|---|
| 1 | Entire system | Not built | Phases B–E in PLAN.md |
| 2 | WorkBuddy custom connector on owner's edition | Docs only | EXP-1 |
| 3 | Long-poll loop in WorkBuddy | Untested | EXP-2 |
| 4 | Tracer-study figures | 2010/2013 | Find latest MOHE tracer study |
| 5 | RYSE and KRI figures | Secondary reports | Read primary reports |
| 6 | 60% failure rate | Weak sourcing | Present only as "commonly cited estimate" or drop |
| 7 | Competitor features | Vendor pages | Hands-on check |

## 8. Glossary

| Term | Plain meaning |
|---|---|
| Agent | An AI component with one job and specific tools |
| Business Model Canvas (BMC) | A one-page, 9-block description of how a business works |
| MCP | Model Context Protocol, a standard way for AI apps to call external tools |
| WorkBuddy | Tencent's desktop AI agent; mandatory for this track |
| Hybrid search | Finding documents by meaning (vectors) and by keywords together |
| Gate | A checkpoint where the user must approve before the agents continue |

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

*References checked via search summaries on 2026-10-10 (full text not yet read for 2–6). No (Built) claims exist yet: no code, tests or deployment as of 2026-10-10.*
