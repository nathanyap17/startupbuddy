# AGENTS.md: Agent roster (16 agents)

> Decided 2026-10-10. ADK types refer to `google-adk` (see `.claude/skills/google-adk/SKILL.md`). Every agent can call `search_knowledge` (hybrid RAG). Every tool call is logged to `agent_event`.

## Topology

```
StartupPipeline (custom BaseAgent orchestrator; reads gates from DB, so it is resumable)
├── Phase 1  problem_coordinator (LlmAgent, router)
│     tools: places_nearby · opendosm_lookup · search_knowledge · enqueue_workbuddy_task(desk_research)
│            save_problem_statement · add_evidence
│     → ⏸ G1: user confirms / edits problem statement
├── Phase 2  bmc_waves (SequentialAgent of 3 ParallelAgents)
│     Wave 1 ║ customer_segments · value_propositions
│     Wave 2 ║ channels · customer_relationships · key_activities · key_resources · key_partners
│     Wave 3 ║ revenue_streams · cost_structure
├── Phase 3  council (ParallelAgent of 5) → aggregate_verdict (deterministic BaseAgent)
│     if any block scores < threshold and round < 2 → re-run only those BMC agents with council notes
│     → enqueue_workbuddy_task(report_builder, financial_sheet, one_pager)
└── Phase 4  advisor (LlmAgent)
      reads: problem statement, canvas, verdict, open `needs_verification` items
      proposes: action_item[] (meeting, email draft, drive folder, checklist)
      → ⏸ G2: user approves per action → executes approved ones via Google Workspace MCP (MCPToolset)
```

## Roster

| # | Agent | Phase | Writes | Key tools | Notes |
|---|---|---|---|---|---|
| 1 | `problem_coordinator` | 1 | `problem_statement`, `evidence_item` | places_nearby, opendosm_lookup, search_knowledge, desk_research (WorkBuddy) | Reverse-engineers the intent into who / where / pain / demand / competition |
| 2 | `customer_segments` | 2·W1 | `bmc_block` | search_knowledge, read_problem | |
| 3 | `value_propositions` | 2·W1 | `bmc_block` | search_knowledge, read_problem, places_nearby | Must state the differentiation against named nearby competitors |
| 4 | `channels` | 2·W2 | `bmc_block` | read_blocks(CS,VP) | |
| 5 | `customer_relationships` | 2·W2 | `bmc_block` | read_blocks(CS,VP) | |
| 6 | `key_activities` | 2·W2 | `bmc_block` | read_blocks(CS,VP), search_knowledge | Licences, permits (SSM, local council, food handler) |
| 7 | `key_resources` | 2·W2 | `bmc_block` | read_blocks(CS,VP) | |
| 8 | `key_partners` | 2·W2 | `bmc_block` | search_knowledge (programmes, suppliers) | Organisations only, never scraped individuals |
| 9 | `revenue_streams` | 2·W3 | `bmc_block` | read_blocks(all) | Prices labelled `estimated` with method |
| 10 | `cost_structure` | 2·W3 | `bmc_block` | read_blocks(all), search_knowledge | Rent, wages, licences: labelled |
| 11 | `council_customer` | 3 | `council_review` | read_canvas | "Would I buy this, at this price, here?" |
| 12 | `council_ceo` | 3 | `council_review` | read_canvas | Strategy, focus, execution risk |
| 13 | `council_investor` | 3 | `council_review` | read_canvas, search_knowledge | Market size, defensibility, fundability (MY programmes) |
| 14 | `council_cfo` | 3 | `council_review` | read_canvas | Unit economics, break-even; recomputes arithmetic in code |
| 15 | `council_mentor` | 3 | `council_review` | read_canvas, search_knowledge | Next 30 days; what to verify first |
| 16 | `advisor` | 4 | `action_item` | Google Workspace MCP (after G2), search_knowledge | Takes tasks from the other agents' decisions |

## Council review shape (each of 5)
`{ seat, scores: {block_key: 1-5}, strengths[], risks[], must_verify[], improve[], verdict: go|revise|stop }`.
Aggregation (code, not LLM): mean per block; a block is sent back if its mean < 3.0 or ≥2 seats flag it in `risks`; overall verdict = majority, ties → `revise`.

## WorkBuddy task skills (run by WorkBuddy, not ADK)

| Skill | Enqueued by | Output |
|---|---|---|
| `desk_research` | problem_coordinator | market notes + source URLs (JSON) |
| `report_builder` | pipeline after Phase 3 | industrial-style report (DOCX/PDF) |
| `financial_sheet` | pipeline after Phase 3 | XLSX: costs, pricing, break-even |
| `one_pager` | pipeline after Phase 3 | PPTX/PDF pitch one-pager (attachment for Advisor emails) |

Definitions: `workbuddy/skills/`. Contract: `docs/MCP_CONTRACT.md`.
