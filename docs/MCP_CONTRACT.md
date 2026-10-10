# MCP_CONTRACT.md: WorkBuddy-facing MCP server

> Endpoint: `POST/GET {PUBLIC_BASE_URL}/mcp`, transport **streamable HTTP**. Auth: header `X-API-Key: <MCP_API_KEY>` (WorkBuddy custom connector "API Key" option). Decided 2026-10-10.
> Constraint: WorkBuddy expects a tool response within ~30 s and a connect timeout of 30 000 ms [WorkBuddy connector docs]. **No tool may block longer than 25 s.**

## Why a queue
MCP is client→server only: WorkBuddy calls us; we cannot call WorkBuddy. ADK agents therefore enqueue `workbuddy_task` rows, and WorkBuddy pulls them.

```
agent ──enqueue──► workbuddy_task(status=queued, deadline_at)
WorkBuddy ──await_next_task(wait_s≤25)──► claims oldest queued (FOR UPDATE SKIP LOCKED), lease 120 s
WorkBuddy runs skill  ──heartbeat_task (optional, extends lease)
WorkBuddy ──submit_task_result──► status=succeeded, result JSON validated → agent wakes (asyncio Event / LISTEN-NOTIFY)
lease expires → re-queued (attempts+1, max 2) · deadline passes → status=expired → agent fallback (labelled)
```

## Tools

| Tool | Args | Returns | Notes |
|---|---|---|---|
| `start_session` | `intent: str`, `location: str` | `{session_id, app_url}` | Entry point for "one prompt" from WorkBuddy. Kicks off Phase 1 |
| `get_session_status` | `session_id` | `{phase, gate, progress, app_url}` | For WorkBuddy to tell the user where things are |
| `confirm_gate` | `session_id`, `gate: G1\|G2`, `decision: approve\|edit\|reject`, `notes?`, `action_ids?: list[str]` | `{ok}` | Same effect as the web buttons; G2 requires explicit action ids |
| `await_next_task` | `worker_id: str`, `wait_s: int = 20` (clamped ≤25) | `{task: null}` or `{task_id, skill, session_id, inputs, output_schema, deadline_at}` | Long-poll. Worker loops until told `stop` |
| `heartbeat_task` | `task_id` | `{lease_until}` | Extends lease 120 s |
| `submit_task_result` | `task_id`, `result_json: str`, `artifact_urls?: list[str]` | `{ok, validation_errors[]}` | Rejected if JSON fails `output_schema` → worker may retry |
| `fail_task` | `task_id`, `reason` | `{ok}` | Agent falls back immediately |
| `upload_artifact` | `task_id`, `filename`, `content_base64` | `{url}` | Files (DOCX/XLSX/PPTX) stored in GCS bucket; size cap 10 MB |
| `ask_session` | `session_id`, `question` | `{reply}` | Friendly, grounded Q&A about the session (Session Assistant); ≤24 s |
| `get_session_summary` | `session_id` | markdown | Lets WorkBuddy narrate results in chat |

Tool parameters are **flat scalars/lists** (ADK/MCP pattern; avoid a lone model parameter).

## Task skill output schemas
Defined as Pydantic models in `backend/app/workbuddy/schemas.py` and exported as JSON Schema in `output_schema`. Every factual item has `{claim, value, label: sourced|estimated|needs_verification, source_url?, method?}`.

## Google Workspace MCP (internal, Advisor only)
Mounted at `/mcp-gws`, **not** added to WorkBuddy. Tools: `create_calendar_event(with_meet)`, `create_gmail_draft`, `create_drive_folder`, `upload_to_drive`. Each call must carry an `action_id` whose `approval.status = approved`; the server checks this in code and refuses otherwise. OAuth: demo Google account, consent screen in Testing mode, refresh token in Secret Manager.
