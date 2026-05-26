#!/usr/bin/env bash
# Start API on 8003 (run in one terminal). UI: cd launchpad-ui && npm run dev
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_PORT="${AFFINE_API_PORT:-8003}"

"$ROOT/scripts/dev-reset.sh" 2>/dev/null || true

cd "$ROOT/agent_catalog"
if [ ! -d .venv ]; then
  echo "Missing .venv — run: cd agent_catalog && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi
if [ ! -f .env ]; then
  echo "Missing .env — run: cp .env.example .env and add Azure keys"
  exit 1
fi

source .venv/bin/activate
echo "Starting API on http://127.0.0.1:${API_PORT} (health: /health)"
echo "In another terminal: cd launchpad-ui && npm run dev"
echo "Open http://localhost:5173"
exec uvicorn api.main:app --reload --host 127.0.0.1 --port "$API_PORT"
