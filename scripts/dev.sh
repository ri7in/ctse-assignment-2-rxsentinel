#!/usr/bin/env bash
# Start the full RxSentinel dev stack (Ollama, backend, frontend).
# Requires: ollama, python@3.11, node@20+, pnpm.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "▸ Checking prerequisites..."
# Prefer ~/.local/python-3.11 if present (standalone build), else PATH python3.11.
if [ -x "$HOME/.local/python-3.11/bin/python3.11" ]; then
  PYTHON_BIN="$HOME/.local/python-3.11/bin/python3.11"
elif command -v python3.11 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3.11)"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
else
  echo "✗ no python3 found"; exit 1
fi
echo "  python:  $PYTHON_BIN ($($PYTHON_BIN --version))"

command -v ollama >/dev/null 2>&1 || { echo "✗ ollama not installed"; exit 1; }
command -v pnpm >/dev/null 2>&1 || { echo "✗ pnpm not installed"; exit 1; }

# Make sure the model is available.
MODEL="${OLLAMA_MODEL:-qwen2.5:3b}"
if ! ollama list 2>/dev/null | grep -q "$MODEL"; then
  echo "▸ Pulling $MODEL (one-time)..."
  ollama pull "$MODEL"
fi

# Start ollama serve in background if not already running.
if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "▸ Starting ollama serve..."
  (ollama serve >/tmp/rxsentinel-ollama.log 2>&1 &)
  sleep 2
fi

# Backend: ensure venv + deps, then start uvicorn.
if [ ! -d backend/.venv ]; then
  echo "▸ Creating backend venv with $PYTHON_BIN..."
  (cd backend && "$PYTHON_BIN" -m venv .venv)
  echo "▸ Installing backend dependencies..."
  (cd backend && .venv/bin/pip install -q --upgrade pip && .venv/bin/pip install -q -e ".[dev]")
fi

echo "▸ Starting backend on :8000..."
(cd backend && .venv/bin/uvicorn rxsentinel.app:app --reload --port 8000 \
  >/tmp/rxsentinel-backend.log 2>&1 &)

# Frontend: install + start.
if [ ! -d frontend/node_modules ]; then
  echo "▸ Installing frontend dependencies..."
  (cd frontend && pnpm install)
fi

echo "▸ Starting frontend on :3000..."
echo ""
echo "  Backend:  http://localhost:8000  (logs: /tmp/rxsentinel-backend.log)"
echo "  Frontend: http://localhost:3000"
echo "  Ollama:   http://localhost:11434  (logs: /tmp/rxsentinel-ollama.log)"
echo ""
echo "  Press Ctrl-C to stop the frontend (backend keeps running in bg)."
echo ""
(cd frontend && pnpm dev)
