<#
.SYNOPSIS
    Quick smoke check before trial — health + auth + DB.
#>

$ErrorActionPreference = "Continue"
$Root = Split-Path $PSScriptRoot -Parent

if (Test-Path "$Root\.env") {
    Get-Content "$Root\.env" | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            Set-Item -Path "env:$($matches[1].Trim())" -Value $matches[2].Trim()
        }
    }
}

$apiKey = $env:API_SECRET_KEY
if (-not $apiKey) { $apiKey = $env:SECRET_KEY }

Write-Host "Checking http://localhost:8000/api/health ..."
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/api/health" -TimeoutSec 5
    Write-Host "  status: $($health.status)" -ForegroundColor Green
    Write-Host "  db: $($health.database_connected)  redis: $($health.redis_connected)  llm: $($health.llm_available)"
} catch {
    Write-Host "  FAIL — is backend running? (.\start.ps1)" -ForegroundColor Red
}

if ($apiKey) {
    Write-Host "Checking authenticated /api/generate (expect 422 validation, not 401) ..."
    try {
        $headers = @{ Authorization = "Bearer $apiKey"; "Content-Type" = "application/json" }
        $body = '{"prompt":"short"}'
        Invoke-WebRequest -Uri "http://localhost:8000/api/generate" -Method POST -Headers $headers -Body $body -TimeoutSec 5 | Out-Null
    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        if ($code -eq 401) {
            Write-Host "  FAIL — 401: API_SECRET_KEY mismatch" -ForegroundColor Red
        } elseif ($code -eq 422 -or $code -eq 429) {
            Write-Host "  OK — auth works (got $code as expected for test body)" -ForegroundColor Green
        } else {
            Write-Host "  Response: $code"
        }
    }
}

Write-Host "`nChecking http://localhost:3000 ..."
try {
    $r = Invoke-WebRequest -Uri "http://localhost:3000" -TimeoutSec 5 -UseBasicParsing
    if ($r.StatusCode -eq 200) {
        Write-Host "  Frontend OK" -ForegroundColor Green
    }
} catch {
    Write-Host "  FAIL — is frontend running?" -ForegroundColor Red
}

Write-Host "`nDone. Open http://localhost:3000 to start a trial generation."
