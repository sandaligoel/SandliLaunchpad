#!/usr/bin/env bash
# Start AFFINE backend API (run in one terminal). UI: cd frontend && npm run dev
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=ports.sh
source "$ROOT/scripts/ports.sh"
API_PORT="$AFFINE_API_PORT"

"$ROOT/scripts/dev-reset.sh" 2>/dev/null || true

cd "$ROOT/backend"
if [ ! -d .venv ]; then
  echo "Missing .venv — run: cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi
if [ ! -f .env ]; then
  echo "Missing .env — run: cp .env.example .env and add Azure keys"
  exit 1
fi

source .venv/bin/activate
echo "Starting API on ${AFFINE_API_TARGET} (health: /health)"
echo "In another terminal: cd frontend && npm run dev"
echo "Open ${UI_URL}"
exec uvicorn api.main:app --reload --host 127.0.0.1 --port "$API_PORT"
