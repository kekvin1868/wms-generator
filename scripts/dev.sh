#!/usr/bin/env bash
# Travel Bag Co. — start backend (FastAPI) + frontend (Next.js) together.
# Stops both on Ctrl+C.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# --- backend ---
if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
elif [[ -d venv ]]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
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
