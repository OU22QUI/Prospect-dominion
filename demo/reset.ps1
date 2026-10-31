Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "Stopping containers and removing volumes..."
docker compose down -v --remove-orphans

Write-Host "Resetting demo data..."
Remove-Item -Force "demo/data/synthetic_signals.csv" -ErrorAction SilentlyContinue

Write-Host "Demo reset complete."
