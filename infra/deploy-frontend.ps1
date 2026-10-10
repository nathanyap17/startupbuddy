# Build the web app against the Cloud Run backend and deploy to Firebase Hosting (owner runs).
$ErrorActionPreference = "Stop"
$P = "dormathon-workspace-1"; $R = "asia-southeast1"
$Root = Resolve-Path "$PSScriptRoot\.."
$url = gcloud run services describe startupbuddy-api --project $P --region $R --format="value(status.url)"
if (-not $url) { throw "Deploy the backend first (infra\deploy-backend.ps1)" }
Push-Location "$Root\frontend"
$env:VITE_API_BASE_URL = $url
npm run build
Pop-Location
Push-Location $Root
firebase deploy --only hosting --project $P
Pop-Location
Write-Host "Landing page: https://$P.web.app"
