# Fervo OMOC — local run script (Windows PowerShell)
# Creates a virtual environment, installs dependencies, starts the app, opens the browser.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
}
Write-Host "Installing dependencies..." -ForegroundColor Cyan
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet

$port = 8000
Write-Host "Starting OMOC app at http://127.0.0.1:$port  (Ctrl+C to stop)" -ForegroundColor Green
Start-Process "http://127.0.0.1:$port"
& ".\.venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port $port
