# StartupBuddy

![StartupBuddy: From idea to first meeting.](docs/brand/banner.png)

StartupBuddy - An agentic AI solution that takes aspiring Malaysian founders from a vague business idea to a locally validated, council-reviewed business model and their first booked stakeholder meetings, powered by Tencent WorkBuddy.

**From idea to first meeting.**

One sentence of intent → grounded problem statement → 9-block Business Model Canvas → 5-seat council review → approved first actions. Built for **Dormathon Track 2: WorkBuddy Agentic Solutions**, scoped to Malaysia (incl. Sarawak).

- **How it works:** 16 Google ADK agents on Cloud Run; Tencent WorkBuddy executes research and document skills through an MCP task queue; a React canvas shows the agents working live.
- **Start here:** `CLAUDE.md` → `PLAN.md` → `docs/`.
- **Live:** landing + app at https://dormathon-workspace-1.web.app · API at https://startupbuddy-api-960127792850.asia-southeast1.run.app
- **Design system:** `docs/DESIGN.md` (Serene Executive Slate, Manrope); brand assets in `docs/brand/`.

## Run locally
```bash
docker compose up -d db                                     # Postgres on host port 5433
cd backend && uv sync && uv run uvicorn app.main:app --port 8000
cd frontend && npm install && npm run dev                   # http://localhost:5173
```

## Deploy (Windows PowerShell, from this folder)
```powershell
powershell -ExecutionPolicy Bypass -File infra\setup-cloud.ps1      # once
powershell -ExecutionPolicy Bypass -File infra\deploy-backend.ps1   # Cloud Run
powershell -ExecutionPolicy Bypass -File infra\deploy-frontend.ps1  # Firebase Hosting
```

## Team
SMILING FACE WITH SUNGLASSES: Nathan Yap (leader), Abraham Pang, Malcolm Sim, Zoe Tan.
