# One-time cloud setup for StartupBuddy (owner runs; safe to re-run: existing items are skipped).
# Creates: Cloud SQL database + user, secrets (DB URL, MCP API key), IAM for the Cloud Run service account.
# Secret values are generated here and never printed, except the MCP key, which you need for WorkBuddy.
$ErrorActionPreference = "Stop"
$P = "dormathon-workspace-1"; $R = "asia-southeast1"; $I = "startupbuddy-db"
$Conn = "${P}:${R}:${I}"
$PN = (gcloud projects describe $P --format="value(projectNumber)")
$SA = "$PN-compute@developer.gserviceaccount.com"

function New-Secret([string]$name, [string]$value) {
  $exists = gcloud secrets list --project $P --filter="name~$name$" --format="value(name)"
  if (-not $exists) { gcloud secrets create $name --project $P --replication-policy=automatic | Out-Null }
  $tmp = New-TemporaryFile
  [IO.File]::WriteAllText($tmp, $value)
  gcloud secrets versions add $name --project $P --data-file=$tmp | Out-Null
  Remove-Item $tmp
  Write-Host "secret $name updated"
}
function New-Token([int]$n) { -join ((48..57) + (97..122) | Get-Random -Count $n | ForEach-Object { [char]$_ }) }

# Database + user
if (-not (gcloud sql databases list --instance $I --project $P --format="value(name)" | Select-String -SimpleMatch "startupbuddy")) {
  gcloud sql databases create startupbuddy --instance $I --project $P
}
$dbPass = New-Token 28
if (gcloud sql users list --instance $I --project $P --format="value(name)" | Select-String -SimpleMatch "startupbuddy") {
  gcloud sql users set-password startupbuddy --instance $I --project $P --password $dbPass | Out-Null
} else {
  gcloud sql users create startupbuddy --instance $I --project $P --password $dbPass | Out-Null
}
New-Secret "startupbuddy-db-url" "postgresql+asyncpg://startupbuddy:$dbPass@/startupbuddy?host=/cloudsql/$Conn"

# MCP API key for WorkBuddy (printed once: paste it into WorkBuddy's mcp.json, keep it private)
$mcpKey = New-Token 32
New-Secret "mcp-api-key" $mcpKey
Set-Content -Path "$PSScriptRoot\..\..\sandbox\.mcp_api_key_cloud" -Value $mcpKey -NoNewline

# IAM for the Cloud Run runtime service account
foreach ($role in @("roles/secretmanager.secretAccessor", "roles/cloudsql.client", "roles/aiplatform.user", "roles/serviceusage.serviceUsageConsumer")) {
  gcloud projects add-iam-policy-binding $P --member="serviceAccount:$SA" --role=$role --condition=None | Out-Null
  Write-Host "granted $role to $SA"
}
Write-Host ""
Write-Host "Done. MCP key saved to dormathon-workspace\sandbox\.mcp_api_key_cloud (not in git). Next: infra\deploy-backend.ps1"
