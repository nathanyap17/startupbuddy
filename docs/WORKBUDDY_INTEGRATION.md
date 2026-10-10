# WORKBUDDY_INTEGRATION.md

> Decided 2026-10-10: **task-queue pattern.** Verified facts are from docs read on 2026-10-10. UI menu names are (Pending) until EXP-1 is run on the owner's WorkBuddy.

## What we know (from docs)
| Fact | Source |
|---|---|
| Custom connectors take an MCP server URL; transport `streamable_http` | Tencent Cloud, WorkBuddy Enterprise connector management |
| Auth options: MCP OAuth 2.1, OAuth 2.0 (auth code), **API Key header** (default `X-API-Key`) | same |
| Remote servers: `streamableHttp` or `sse`; production must be HTTPS | WorkBuddy connector developer docs |
| Tool responses expected within **30 s**, connect timeout 30 000 ms | same |
| Personal edition user-token mode needs WorkBuddy ≥ 4.23.0 | same |
| MCP servers load at session start; new/trusted servers need a new WorkBuddy session | community report (Pending) |
| WorkBuddy automations run only while the desktop app is open | Tencent Cloud dev community article |
| WorkBuddy spawns a `cbc` (CodeBuddy Code) child process; headless `cbc -p` exists with `CODEBUDDY_API_KEY` | CodeBuddy CLI docs |

## Why not "server calls WorkBuddy"
In MCP, WorkBuddy is the **client**. Our server can only answer calls. WorkBuddy also runs on a laptop that is not reachable from Cloud Run. Hence the queue: agents enqueue, WorkBuddy pulls.

## Setup (owner, once)
1. Deploy the backend to Cloud Run so `https://<run-url>/mcp` is public. No tunnel (decided 2026-10-10): local runs are tested with pytest and an MCP client script; WorkBuddy is always pointed at Cloud Run. Use the **direct Run URL**, not a Firebase Hosting rewrite (Firebase cuts proxied requests at ~60 s).
2. WorkBuddy → **MCP Server Management** → **Add MCP**. This opens a JSON editor for `C:\Users\User\.workbuddy-ai\mcp.json` (seen 2026-10-10, screenshot `../workbuddy/workbuddy-add-mcp.png`). Add:
   ```json
   {
     "mcpServers": {
       "startupbuddy": {
         "type": "http",
         "url": "https://<run-url>/mcp",
         "headers": { "X-API-Key": "<MCP_API_KEY value>" }
       }
     }
   }
   ```
   **The URL must end in `/mcp`** (EXP-1: without it WorkBuddy hits `/` and shows "SSE error: Non-200 status code (404)"). The key lives only in this local file and in Secret Manager, never in the repo. The format follows the CodeBuddy `mcpServers` schema (`type` `http`/`sse`, `url`, `headers`); confirm in EXP-1 that `"type": "http"` is accepted.
3. Import skills from `workbuddy/skills/` (the worker plus four task skills).
4. Start a **new** WorkBuddy session so the connector loads.
5. Test: ask WorkBuddy "list StartupBuddy tools", then "Start StartupBuddy worker".

## Run-time behaviour
- The worker skill loops: `await_next_task` → if task, load the named skill, do the work, `upload_artifact` for files, `submit_task_result` → repeat. Stops when the user says stop or after 20 idle polls (≈8 min). EXP-2: ≈1.4 credits per poll, ≈25–30 s per empty poll at `wait_s=20`.
- Web app shows **WorkBuddy: online** when a poll arrived in the last 60 s (from `worker_id` heartbeat).

## Demo checklist
- WorkBuddy open, logged in, connector enabled, fresh session, worker running **before** the demo starts.
- Laptop power settings: no sleep.
- Fallback: seeded completed session.
