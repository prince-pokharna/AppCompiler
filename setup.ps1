<#
.SYNOPSIS
    AppCompiler — one-time dependency setup for local trial.
#>

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "       AppCompiler Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Root .env
if (-not (Test-Path "$Root\.env")) {
    Copy-Item "$Root\.env.example" "$Root\.env"
    Write-Host "`nCreated .env — add your OPENAI_API_KEY and API_SECRET_KEY before starting." -ForegroundColor Yellow
}

# Backend
Write-Host "`n1. Backend (Python)..." -ForegroundColor Yellow
Set-Location "$Root\backend"

if (-not (Test-Path ".\venv")) {
    python -m venv venv
}

& .\venv\Scripts\python.exe -m pip install --upgrade pip -q
& .\venv\Scripts\python.exe -m pip install -r requirements.txt -q

Set-Location $Root

# Frontend
Write-Host "2. Frontend (Node)..." -ForegroundColor Yellow
Set-Location "$Root\frontend"
npm install
Set-Location $Root

Write-Host "`n==========================================" -ForegroundColor Green
Write-Host "Setup complete. Next steps:" -ForegroundColor Green
Write-Host "  1. Edit .env — set OPENAI_API_KEY and API_SECRET_KEY"
Write-Host "  2. Run:  .\start.ps1"
Write-Host "  3. Open: http://localhost:3000"
Write-Host "==========================================" -ForegroundColor Green
