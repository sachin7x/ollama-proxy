#!/usr/bin/env bash
# setup.sh — one-time project setup with uv (Linux / macOS)
# Prerequisites: curl -LsSf https://astral.sh/uv/install.sh | sh
set -euo pipefail

echo "=== ollama-proxy setup ==="

echo ""
echo "[1/3] Syncing dependencies..."
uv sync --dev

echo ""
if [ ! -f .env ]; then
    cp .env.example .env
    echo "[2/3] Created .env from .env.example"
    echo "      --> Edit .env and add your API keys before starting the server."
else
    echo "[2/3] .env already exists — skipping"
fi

echo ""
echo "[3/3] Setup complete."
echo ""
echo "  Start server :  uv run uvicorn main:app --host 0.0.0.0 --port 11434 --reload"
echo "  Run tests    :  uv run pytest tests/ -v"
echo "  Smoke test   :  curl http://localhost:11434/"
