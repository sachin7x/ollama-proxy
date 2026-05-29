# setup.ps1 — one-time project setup with uv
# Run this once after cloning the repo.
#
# Prerequisites: install uv from https://docs.astral.sh/uv/getting-started/installation/
#   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "=== ollama-proxy setup ===" -ForegroundColor Cyan

# 1. Create virtual environment and install all deps (main + dev)
Write-Host "`n[1/3] Syncing dependencies with uv..." -ForegroundColor Yellow
uv sync --dev

# 2. Copy .env if not present
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "`n[2/3] Created .env from .env.example" -ForegroundColor Yellow
    Write-Host "      --> Open .env and add your API keys before starting the server." -ForegroundColor Green
} else {
    Write-Host "`n[2/3] .env already exists - skipping" -ForegroundColor Yellow
}

# 3. Confirm
Write-Host "`n[3/3] Setup complete." -ForegroundColor Green
Write-Host ""
Write-Host "  Start server:    uv run uvicorn main:app --host 0.0.0.0 --port 11434 --reload"
Write-Host "  Run tests:       uv run pytest tests/ -v"
Write-Host "  Quick smoke:     curl http://localhost:11434/"
