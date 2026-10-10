---
name: startupbuddy-worker
description: Run StartupBuddy with WorkBuddy. Use when the user wants to start a business idea session in StartupBuddy (e.g. "Use StartupBuddy: I want to sell kolo mee near Padungan") or says "start the StartupBuddy worker". Starts a session and then works through StartupBuddy's task queue until told to stop.
---

# StartupBuddy worker (DRAFT 2026-10-10; validate in EXP-2/EXP-3)

Requires the **StartupBuddy** MCP connector (tools: `start_session`, `await_next_task`, `submit_task_result`, `upload_artifact`, `fail_task`, `heartbeat_task`, `get_session_status`, `confirm_gate`, `get_session_summary`).

## If the user gave a business intent
1. Extract `intent` (what they want to do) and `location` (a Malaysian place). Ask once if the location is missing.
2. Call `start_session(intent, location)`. Tell the user the `app_url` so they can watch the canvas.
3. Go to the worker loop.

## Worker loop
Repeat:
1. Call `await_next_task(worker_id="workbuddy-<machine>", wait_s=20)`.
2. If `task` is null: continue looping (say nothing). After 20 empty polls in a row (~8 min), stop and tell the user (idle polls cost credits: EXP-2 measured about 1.4 credits per poll).
3. If a task arrives: open the skill named in `task.skill` (`startupbuddy-desk-research`, `startupbuddy-report-builder`, `startupbuddy-financial-sheet`, `startupbuddy-one-pager`) and follow it with `task.inputs`.
4. For long work, call `heartbeat_task(task_id)` about every 60 s.
5. Upload files with `upload_artifact`, then call `submit_task_result(task_id, result_json, artifact_urls)`. `result_json` must match `task.output_schema`. If `validation_errors` come back, fix and resubmit once; otherwise `fail_task`.
6. Briefly tell the user what you finished (one line).

## Gates
When `get_session_status` shows a gate waiting (G1 problem statement, G2 actions), summarise it for the user and ask. Pass their answer with `confirm_gate`. **Never approve G2 actions on the user's behalf.**

## Rules
- Every factual figure in a result has `label` = `sourced` (with `source_url`), `estimated` (with `method`) or `needs_verification`.
- Do not look up private individuals' contact details.
- Stop when the user says stop.
