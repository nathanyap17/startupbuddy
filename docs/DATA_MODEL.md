# DATA_MODEL.md

> Engine: PostgreSQL 16 + `pgvector` (local Docker, Cloud SQL in cloud). ORM: SQLAlchemy 2.0 async (`asyncpg`), migrations with Alembic. IDs: ULID strings (`CHAR(26)`). Timestamps: `TIMESTAMPTZ` stored UTC, displayed `Asia/Kuching`. JSON: `JSONB`. Drafted 2026-10-10. Becomes authoritative once the first migration exists.

## Enumerations

| Enum | Values |
|---|---|
| `session_phase` | `intake`, `problem`, `gate_g1`, `bmc`, `council`, `deliverables`, `advisor`, `gate_g2`, `actions`, `done`, `failed` |
| `bmc_block_key` | `customer_segments`, `value_propositions`, `channels`, `customer_relationships`, `key_activities`, `key_resources`, `key_partners`, `revenue_streams`, `cost_structure` |
| `council_seat` | `customer`, `ceo`, `investor`, `cfo`, `mentor` |
| `evidence_label` | `sourced`, `estimated`, `needs_verification` |
| `task_status` | `queued`, `claimed`, `succeeded`, `failed`, `expired` |
| `action_kind` | `calendar_event`, `gmail_draft`, `drive_folder`, `checklist` |
| `approval_status` | `pending`, `approved`, `rejected`, `executed`, `exec_failed` |
| `kb_namespace` | `national`, `sarawak`, `framework`, `session` (user-specific notes) |

## 1 · `demo_user`
| Field | Type | ? | Notes |
|---|---|---|---|
| id | ulid | | single seeded row |
| display_name | text | | |
| email | text | ✓ | Google account used for Advisor actions |
| created_at | timestamptz | | |

## 2 · `startup_session`
| Field | Type | ? | Notes |
|---|---|---|---|
| id | ulid | | |
| user_id | ulid FK demo_user | | |
| title | text | | auto from intent |
| intent | text | | the user's one sentence |
| location_text | text | | e.g. "Padungan, Kuching" |
| lat, lng | double | ✓ | geocoded |
| phase | session_phase | | |
| revision_round | int | | 0–2 |
| origin | text | | `web` or `workbuddy` |
| created_at, updated_at | timestamptz | | |

## 3 · `problem_statement`
| Field | Type | ? | Notes |
|---|---|---|---|
| id | ulid | | |
| session_id | ulid FK | | unique per version |
| version | int | | user edits create new versions |
| statement | text | | |
| target_user, pain, why_now | text | | |
| confirmed_at | timestamptz | ✓ | set by G1 |

## 4 · `evidence_item`
| Field | Type | ? | Notes |
|---|---|---|---|
| id | ulid | | |
| session_id | ulid FK | | |
| scope | text | | `problem` or a `bmc_block_key` |
| claim | text | | |
| value | text | ✓ | |
| label | evidence_label | | **required** (rule 2) |
| source_url | text | ✓ | required if `sourced` |
| method | text | ✓ | required if `estimated` |
| produced_by | text | | agent or skill name |

**Constraint:** `CHECK (label <> 'sourced' OR source_url IS NOT NULL)` and `CHECK (label <> 'estimated' OR method IS NOT NULL)`.

## 5 · `bmc_block`
| Field | Type | ? | Notes |
|---|---|---|---|
| id | ulid | | |
| session_id | ulid FK | | |
| key | bmc_block_key | | |
| round | int | | 0 initial, 1–2 revisions |
| content | jsonb | | `{summary, items[], assumptions[]}` |
| status | text | | `pending`, `thinking`, `done`, `revising` |

**Constraint:** unique (`session_id`, `key`, `round`).

## 6 · `council_review`
| Field | Type | ? | Notes |
|---|---|---|---|
| id | ulid | | |
| session_id | ulid FK | | |
| seat | council_seat | | |
| round | int | | |
| scores | jsonb | | `{block_key: 1..5}` |
| strengths, risks, must_verify, improve | jsonb | | lists |
| verdict | text | | `go`, `revise`, `stop` |

## 7 · `council_verdict`
Deterministic aggregate per round: `session_id`, `round`, `block_means jsonb`, `blocks_to_revise text[]`, `overall text`.

## 8 · `workbuddy_task` (the queue)
| Field | Type | ? | Notes |
|---|---|---|---|
| id | ulid | | |
| session_id | ulid FK | | |
| skill | text | | `desk_research`, `report_builder`, `financial_sheet`, `one_pager` |
| inputs | jsonb | | |
| output_schema | jsonb | | JSON Schema |
| status | task_status | | |
| worker_id | text | ✓ | |
| lease_until | timestamptz | ✓ | |
| deadline_at | timestamptz | | after this → `expired` |
| attempts | int | | max 2 |
| result | jsonb | ✓ | validated |
| error | text | ✓ | |
| created_at, claimed_at, finished_at | timestamptz | ✓ | |

**Index:** (`status`, `created_at`) for claim. Claim with `SELECT … FOR UPDATE SKIP LOCKED`.

## 9 · `artifact`
`id`, `session_id`, `task_id?`, `kind` (`report`, `financial_sheet`, `one_pager`, `other`), `filename`, `gcs_uri`, `public_url?`, `size_bytes`, `created_at`.

## 10 · `action_item`
| Field | Type | ? | Notes |
|---|---|---|---|
| id | ulid | | |
| session_id | ulid FK | | |
| kind | action_kind | | |
| title, rationale | text | | rationale cites the agent decision it came from |
| payload | jsonb | | e.g. attendees, time, email body |
| source_agent | text | | which agent's decision produced it |
| approval | approval_status | | rule 1 |
| decided_at, executed_at | timestamptz | ✓ | |
| external_ref | text | ✓ | Calendar event id / draft id / Drive folder id |

## 11 · `agent_event` (audit log + canvas feed)
`id`, `session_id`, `ts`, `agent`, `kind` (`start`, `thought`, `tool_call`, `tool_result`, `handoff`, `done`, `error`, `fallback`), `target` (block key or null), `summary text`, `detail jsonb`, `latency_ms int?`. Streamed via SSE in insert order.

## 12 · `kb_document` / `kb_chunk` (hybrid RAG)
`kb_document`: `id`, `namespace`, `title`, `source_url`, `publisher`, `retrieved_on date`, `session_id?` (only for `session` namespace).
`kb_chunk`: `id`, `document_id FK`, `ordinal`, `text`, `embedding vector(768)`, `tsv tsvector GENERATED ALWAYS AS (to_tsvector('simple', text)) STORED`.
**Indexes:** HNSW on `embedding` (cosine), GIN on `tsv`. Query = top-k vector ∪ top-k full-text, fused by RRF (k=60). Dimension 768 fits EmbeddingGemma; revisit if EXP-5 picks another model.

## Privacy & retention
| Concern | Handling |
|---|---|
| Personal contact data | Never scraped. Attendee emails only come from the user (rule 3) |
| Google OAuth tokens | Secret Manager, never DB or repo |
| Demo data | Single demo user; sessions can be deleted from the UI (hard delete cascades) |
| Logs | `agent_event` stores summaries, not raw secrets or full email bodies of third parties |
