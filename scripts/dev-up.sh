#!/usr/bin/env bash
# Prepare local dev: sync UI ports, verify Azure-backed API is reachable.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=ports.sh
source "$ROOT/scripts/ports.sh"

echo "=== AFFINE dev stack ==="
echo "Ports (config/dev-ports.json):"
echo "  Backend API ${AFFINE_API_TARGET}"
echo "  Mock API    ${MOCK_API_TARGET}"
echo "  Frontend    ${UI_URL}"
echo ""

"$ROOT/scripts/sync-dev-env.sh"
echo ""

if [ ! -f "$ROOT/backend/.env" ]; then
  echo "WARN: Missing backend/.env — copy from backend/.env.example and add Azure keys."
  echo "      Without AZURE_STORAGE_* sessions will not persist to Azure Blob."
  exit 1
fi

cd "$ROOT/backend"
if [ ! -d .venv ]; then
  echo "WARN: Run: cd backend && python3 -m venv .venv && pip install -r requirements.txt"
fi

if curl -sf -m 3 "${AFFINE_API_TARGET}/health" >/dev/null 2>&1; then
  health=$(curl -s "${AFFINE_API_TARGET}/health")
  echo "Backend API: running"
  echo "  $health" | python3 -m json.tool 2>/dev/null || echo "  $health"
else
  echo "Backend API: not running — start in another terminal:"
  echo "  ./scripts/start-backend.sh"
fi

echo ""
echo "Then:"
echo "  Terminal 2 (optional): ./scripts/start-mock-api.sh"
echo "  Terminal 3:            cd frontend && npm run dev"
echo ""
echo "Open: ${UI_URL}/interview"
