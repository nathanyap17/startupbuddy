# CREDENTIALS.md: names and locations only, NEVER values

> Real values live in `backend/.env` (gitignored) locally and in **Secret Manager** on Cloud Run. Template: `backend/.env.example`.

## Environment variables

| Variable | Used by | Where it lives | Notes |
|---|---|---|---|
| `DATABASE_URL` | backend | `.env` / Secret `startupbuddy-db-url` | `postgresql+asyncpg://…`; cloud uses the Cloud SQL socket |
| `GOOGLE_GENAI_USE_VERTEXAI` | ADK | env | `TRUE` |
| `GOOGLE_CLOUD_PROJECT` | ADK, GCS | env | `dormathon-workspace-1` |
| `GOOGLE_CLOUD_LOCATION` | ADK | env | model region (EXP-4) |
| `GEMINI_MODEL` | ADK | env | explicit id, pinned after EXP-4 |
| `EMBEDDING_BACKEND` | rag | env | `embeddinggemma` or `vertex` (EXP-5) |
| `EMBEDDING_MODEL` | rag | env | e.g. `google/embeddinggemma-300m` |
| `HF_TOKEN` | rag (EmbeddingGemma download) | `.env` / Secret `hf-token` | only if model is gated |
| `MAPS_API_KEY` | tools.places | `.env` / Secret `maps-api-key` | Places API (New); restrict by API |
| `MCP_API_KEY` | WorkBuddy MCP auth | `.env` / Secret `mcp-api-key` | same value entered in WorkBuddy connector |
| `GWS_OAUTH_CLIENT_JSON` | Google Workspace MCP | Secret `gws-oauth-client` | OAuth client (Desktop/Web), consent screen in Testing |
| `GWS_REFRESH_TOKEN` | Google Workspace MCP | Secret `gws-refresh-token` | demo account only |
| `ARTIFACT_BUCKET` | artifacts | env | `startupbuddy-artifacts` |
| `PUBLIC_BASE_URL` | MCP, links | env | `http://localhost:8000` locally, Run URL in cloud |
| `FRONTEND_ORIGIN` | CORS | env | `http://localhost:5173` / Firebase URL |
| `AGENT_TURN_TIMEOUT_S` | agents | env | default 60 |
| `WORKBUDDY_TASK_DEADLINE_S` | queue | env | default 300 |
| `VITE_API_BASE_URL` | frontend | `frontend/.env.local` | not secret |

## Deployed URLs

| Environment | URL | Notes |
|---|---|---|
| Backend (Cloud Run `startupbuddy-api`) | https://startupbuddy-api-960127792850.asia-southeast1.run.app | deployed 2026-10-10 18:20 MYT; alias https://startupbuddy-api-da73njvkmq-as.a.run.app |
| Frontend (Firebase Hosting) | > not deployed | `https://dormathon-workspace-1.web.app` expected once Firebase is attached |
| WorkBuddy connector | https://startupbuddy-api-960127792850.asia-southeast1.run.app/mcp | key = Secret `mcp-api-key` (copy in `../sandbox/.mcp_api_key_cloud`) |
| GitHub | https://github.com/nathanyap17/startupbuddy | not pushed yet |

## Post-deploy checklist
1. `GET /health` returns `{ok:true, db:true}`.
2. WorkBuddy connector re-pointed to the Run URL; new WorkBuddy session; tools listed.
3. `FRONTEND_ORIGIN` matches the Firebase URL (CORS).
4. Create one session end to end; confirm G2 actions land in the demo Google account.
5. Billing alert set on `dormathon-workspace-1`.
