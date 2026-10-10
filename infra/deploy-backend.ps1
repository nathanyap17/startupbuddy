# Deploy the backend to Cloud Run (owner runs). Re-run after code changes; the URL stays the same.
$ErrorActionPreference = "Stop"
$P = "dormathon-workspace-1"; $R = "asia-southeast1"; $Conn = "${P}:${R}:startupbuddy-db"
$Root = Resolve-Path "$PSScriptRoot\.."
$Frontend = if ($env:FRONTEND_ORIGIN) { $env:FRONTEND_ORIGIN } else { "https://$P.web.app,https://$P.firebaseapp.com,http://localhost:5173" }

$secrets = "DATABASE_URL=startupbuddy-db-url:latest,MCP_API_KEY=mcp-api-key:latest"
$hasToken = gcloud secrets list --project $P --filter="name~gws-token$" --format="value(name)"
if ($hasToken) { $secrets += ",/secrets/gws/token.json=gws-token:latest" }

gcloud run deploy startupbuddy-api `
  --source $Root --project $P --region $R --allow-unauthenticated `
  --add-cloudsql-instances $Conn `
  --min-instances 1 --max-instances 1 --timeout 3600 --memory 1Gi --cpu 1 --no-cpu-throttling `
  --set-secrets $secrets `
  --set-env-vars "^@^GOOGLE_CLOUD_PROJECT=$P@GOOGLE_CLOUD_LOCATION=global@GEMINI_MODEL=gemini-3.5-flash@THINKING_LEVEL=LOW@FRONTEND_ORIGIN=$Frontend@GWS_TOKEN_FILE=/secrets/gws/token.json"

$url = gcloud run services describe startupbuddy-api --project $P --region $R --format="value(status.url)"
gcloud run services update startupbuddy-api --project $P --region $R --update-env-vars "PUBLIC_BASE_URL=$url" | Out-Null
Write-Host ""
Write-Host "Backend URL: $url"
Write-Host "Health:      $url/health"
Write-Host "WorkBuddy:   $url/mcp"
