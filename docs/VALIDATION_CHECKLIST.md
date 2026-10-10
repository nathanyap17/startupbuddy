# VALIDATION_CHECKLIST.md

## Status board
| Item | Status | Evidence |
|---|---|---|
| Folder structure + docs | done 2026-10-10 | this commit (pending owner review) |
| ADK refs cloned | done 2026-10-10 | `../adk-python` at v2.6.1, `../adk-docs` main 2026-10-09 |
| WorkBuddy custom connector reaches our MCP | 🔴 untested | EXP-1 |
| Long-poll worker loop | 🔴 untested | EXP-2 |
| Skill returns schema-valid JSON | 🟠 untested | EXP-3 |
| Gemini model id/region | 🟠 untested | EXP-4 |
| Embedding backend | 🟡 untested | EXP-5 |
| Places + OpenDOSM | 🟠 untested | EXP-6 |
| Problem-statement evidence E2–E4 primary sources | 🟠 pending | `docs/PROBLEM_STATEMENT.md` |

## Blocking items
1. WorkBuddy to our MCP connection (EXP-1). UI exists: MCP Server Management edits mcp.json
2. Firebase attached: done 2026-10-10 (project number 960127792850)
3. Billing linked and APIs enabled: done 2026-10-10 (run, artifactregistry, cloudbuild, aiplatform, sqladmin, secretmanager, storage, places, geocoding, calendar, gmail, drive)

## Environment readiness (checked 2026-10-10)
| Tool | Found |
|---|---|
| Python | 3.14.2 (global). **Project should use 3.11/3.12 via uv** (wheel availability for torch/asyncpg) |
| uv | 0.11.32 |
| Node | v24.12.0 |
| Docker | 29.1.3 |
| gcloud | 574.0.0 |
| Firebase CLI | 15.33.0, logged in as `demony11111@gmail.com` (npm global dir added to user PATH) |
| gcloud auth | account `demony11111@gmail.com`, project `dormathon-workspace-1`; ADC quota project `dormathon-workspace-1` |
| git | 2.51.2 |
| WorkBuddy desktop | 5.7.6 (owner, 2026-10-10) |

## Decisions still open
See `PLAN.md` → Open items.

## Log
- 2026-10-10: workspace scaffolded; no code yet.
- 2026-10-10: gcloud, ADC, Firebase, billing ready; WorkBuddy MCP config found (mcp.json).
