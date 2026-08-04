#!/usr/bin/env bash
# Travel Bag Co. — start backend (FastAPI) + frontend (Next.js) together.
# Stops both on Ctrl+C.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# --- backend ---
# Python is managed by pyenv + uv (see .python-version), not Homebrew's
# python@3.12/3.14. This only affects this script's PATH, not your shell.
if [[ -d "$HOME/.pyenv" ]]; then
  export PYENV_ROOT="$HOME/.pyenv"
  export PATH="$PYENV_ROOT/bin:$PATH"
  eval "$(pyenv init -)"
fi

if [[ ! -d .venv ]] && command -v uv >/dev/null 2>&1; then
  echo "No .venv found — creating one with uv ($(cat .python-version 2>/dev/null || echo 'default') )…"
  uv venv --python "$(cat .python-version)" .venv
  uv pip install -r requirements.txt --python .venv/bin/python
fi

if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
elif [[ -d venv ]]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

# Load secrets from .env (root preferred, backend/ fallback)
ENV_FILE=""
if [[ -f .env ]]; then
  ENV_FILE=".env"
elif [[ -f backend/.env ]]; then
  ENV_FILE="backend/.env"
fi
if [[ -n "$ENV_FILE" ]]; then
  echo "Loading env from $ENV_FILE"
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

cleanup() {
  echo "Stopping servers…"
  kill "$BACKEND_PID" 2>/dev/null || true
  kill "${FRONTEND_PID:-}" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# --- frontend ---
cd frontend
if command -v pnpm >/dev/null 2>&1; then
  pnpm dev &
else
  npm run dev &
fi
FRONTEND_PID=$!

wait "$BACKEND_PID" "$FRONTEND_PID"
