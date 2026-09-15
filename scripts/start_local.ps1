$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not $env:PD_API_KEY) {
    $env:PD_API_KEY = "dev-local-key"
}

Write-Host "Starting Prospect Dominion core services..."
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile core up -d --build

Write-Host "Waiting for API readiness..."
Start-Sleep -Seconds 12

python scripts/verify_local.py
