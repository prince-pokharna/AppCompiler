<#
.SYNOPSIS
    AppCompiler — start full stack for local trial.
#>

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "       AppCompiler Trial Startup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

if (-not (Test-Path "$Root\.env")) {
    Write-Host "ERROR: Missing .env at repo root. Run: Copy-Item .env.example .env" -ForegroundColor Red
    exit 1
}

# 1. Docker (Postgres + Redis)
Write-Host "`n1. Starting Postgres and Redis..." -ForegroundColor Yellow
Set-Location $Root
try {
    docker compose up -d postgres redis
    Write-Host "Waiting for databases (10s)..."
    Start-Sleep -Seconds 10
} catch {
    Write-Host "WARNING: Docker failed. Start Docker Desktop, or use SQLite trial mode:" -ForegroundColor Yellow
    Write-Host "  Comment out DATABASE_URL in .env (uses SQLite file) and run: docker compose up -d redis" -ForegroundColor Yellow
}

# 2. Backend venv + migrations
Write-Host "`n2. Backend setup..." -ForegroundColor Yellow
Set-Location "$Root\backend"

if (-not (Test-Path ".\venv")) {
    Write-Host "   Creating venv — run .\setup.ps1 first for full install." -ForegroundColor Red
    exit 1
}

$env:PYTHONPATH = "."
Get-Content "$Root\.env" | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
    }
}

Write-Host "   Running migrations..."
& .\venv\Scripts\alembic.exe upgrade head

# 3. Start backend
Write-Host "`n3. Starting FastAPI (port 8000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$Root\backend'; `$env:PYTHONPATH='.'; Get-Content '$Root\.env' | ForEach-Object { if (`$_ -match '^\s*([^#][^=]+)=(.*)$') { Set-Item -Path env:(`$matches[1].Trim()) -Value `$matches[2].Trim() } }; .\venv\Scripts\activate; uvicorn app.main:app --reload --port 8000"
) -WindowStyle Normal

# 4. Start frontend
Write-Host "`n4. Starting Next.js (port 3000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$Root\frontend'; Get-Content '$Root\.env' | ForEach-Object { if (`$_ -match '^\s*([^#][^=]+)=(.*)$') { Set-Item -Path env:(`$matches[1].Trim()) -Value `$matches[2].Trim() } }; `$env:NEXT_PUBLIC_USE_API_PROXY='true'; npm run dev"
) -WindowStyle Normal

Set-Location $Root

Write-Host "`n==========================================" -ForegroundColor Green
Write-Host "AppCompiler is starting!" -ForegroundColor Green
Write-Host ""
Write-Host "  UI:      http://localhost:3000"
Write-Host "  API:     http://localhost:8000/docs"
Write-Host "  Health:  http://localhost:8000/api/health"
Write-Host ""
Write-Host "Enter a prompt on the UI (e.g. 'Build a CRM with contacts and dashboard')."
Write-Host "First generation may take 2-5 minutes (OpenAI pipeline)."
Write-Host "==========================================" -ForegroundColor Green
