# workbuddy/

Everything that runs **inside Tencent WorkBuddy** (not on our servers).

- `skills/startupbuddy-worker/`: entry skill, starts a session and runs the task-queue loop.
- `skills/startupbuddy-*/`: task skills, one per `workbuddy_task.skill`.

Setup steps: `../docs/WORKBUDDY_INTEGRATION.md`. Tool contract: `../docs/MCP_CONTRACT.md`.
All skills are drafts until EXP-2/EXP-3 pass.
