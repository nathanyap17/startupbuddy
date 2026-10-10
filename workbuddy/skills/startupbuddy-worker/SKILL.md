---
name: startupbuddy-worker
description: "Run StartupBuddy with WorkBuddy. Use when the user wants to start or validate a business idea in Malaysia with StartupBuddy (e.g. 'Use StartupBuddy: I want to sell kolo mee near Padungan, Kuching'), or says 'start the StartupBuddy worker'. Starts a session, then works through StartupBuddy's task queue until the run is done."
version: 0.3.0
allowed-tools: Read,Write,Bash
---

# StartupBuddy worker

Requires the **startupbuddy** MCP server. Tools (exact names):
`mcp__startupbuddy__start_session`, `mcp__startupbuddy__get_session_status`, `mcp__startupbuddy__confirm_gate`,
`mcp__startupbuddy__await_next_task`, `mcp__startupbuddy__heartbeat_task`, `mcp__startupbuddy__submit_task_result`,
`mcp__startupbuddy__fail_task`, `mcp__startupbuddy__upload_artifact`, `mcp__startupbuddy__ask_session`.

## 1. Start (if the user gave a business idea)
1. Extract `intent` (what they want to do) and `location` (a Malaysian place). Ask once if the location is missing.
2. Call `start_session(intent, location)`. Tell the user the `app_url`: the live canvas of 16 agents.
3. Go to the worker loop.

## 2. Worker loop
Repeat:
1. Call `await_next_task(worker_id="workbuddy-laptop", wait_s=25)`.
2. If `task` is null: every 4th empty poll, call `get_session_status` for the session.
   - If `gate_waiting` is `G1`: show the user the `problem_statement` and ask: confirm, or stop? Pass the answer with `confirm_gate(session_id, "G1", "approve"|"reject")`.
   - If `gate_waiting` is `G2`: list the `actions` and ask which to approve. Pass **only the ids the user approved** with `confirm_gate(session_id, "G2", "approve", action_ids=[...])`. **Never approve on the user's behalf.**
   - If `phase` is `done` or `failed`: tell the user and stop.
   - Stop after 20 empty polls in a row (idle polls cost credits).
3. If a task arrives, follow the skill for `task.skill`:
   - `desk_research` → skill **startupbuddy-desk-research**
   - `report_builder` → skill **startupbuddy-report-builder**
4. For work longer than a minute, call `heartbeat_task(task_id)` about every 60 s.
5. Call `submit_task_result(task_id, result_json)` where `result_json` is a JSON **string** matching `task.output_schema`. If `validation_errors` come back, fix them and resubmit once; otherwise call `fail_task(task_id, reason)`.
6. Tell the user in one line what you finished, then continue the loop.

## Questions from the user
If the user asks anything about their plan ("is this worth it?", "what's my break-even?"), call `ask_session(session_id, question)` and relay the reply as is. It's friendly and grounded in the session.

## Always allow
If the user says "always allow" or "approve everything from now on", pass the decision with `confirm_gate` as usual; the web app's Autopilot switches control future checkpoints.

## Rules
- Every factual figure has `label` = `sourced` (only with a `source_url` you actually opened), `estimated` (with `method`) or `needs_verification`.
- Never look up private individuals' contact details.
- Stop when the user says stop.
