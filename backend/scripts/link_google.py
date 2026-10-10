"""Link the demo Google account for the Advisor (Calendar events + Gmail drafts).

Owner runs once, from startupbuddy/backend:
    uv run python scripts/link_google.py
Needs backend/client_secret.json (OAuth client, type "Desktop app"). Opens a browser to sign in,
then writes backend/token.json (gitignored). Upload it as Secret Manager secret `gws-token` with the
command this script prints, then redeploy the backend.
"""
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar.events", "https://www.googleapis.com/auth/gmail.compose"]
HERE = Path(__file__).resolve().parent.parent

secret = HERE / "client_secret.json"
if not secret.exists():
    raise SystemExit(f"Missing {secret}. Download the OAuth client JSON (Desktop app) and save it there.")
flow = InstalledAppFlow.from_client_secrets_file(str(secret), SCOPES)
creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
if not creds.refresh_token:
    raise SystemExit("No refresh token returned. Remove the app's access at myaccount.google.com/permissions and retry.")
out = HERE / "token.json"
out.write_text(creds.to_json(), encoding="utf-8")
print(f"Saved {out}")
print("Next (PowerShell, from startupbuddy/):")
print("  gcloud secrets create gws-token --project dormathon-workspace-1 --replication-policy=automatic")
print("  gcloud secrets versions add gws-token --project dormathon-workspace-1 --data-file=backend\\token.json")
print("  powershell -ExecutionPolicy Bypass -File infra\\deploy-backend.ps1")
