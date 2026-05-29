#!/usr/bin/env bash
# Diagnose local AFFINE dev: ports, backend health, UI proxy target.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=ports.sh
source "$ROOT/scripts/ports.sh"

echo "=== AFFINE doctor ==="
echo ""
echo "Runtime ports (config/runtime-ports.json):"
echo "  API   ${AFFINE_API_TARGET}"
echo "  UI    ${UI_URL}"
echo ""

ok=0
if curl -sf -m 4 "${AFFINE_API_TARGET}/health" >/dev/null 2>&1; then
  echo "OK  Backend responding at ${AFFINE_API_TARGET}/health"
  curl -s "${AFFINE_API_TARGET}/health" | python3 -m json.tool 2>/dev/null | head -12
  ok=1
else
  echo "FAIL  Nothing listening at ${AFFINE_API_TARGET}"
  echo "      Run: ./scripts/start-backend.sh"
fi

echo ""
if [ -f "$ROOT/frontend/.env.local" ]; then
  echo "frontend/.env.local:"
  grep -E "AFFINE|VITE_AFFINE" "$ROOT/frontend/.env.local" || true
else
  echo "WARN  Missing frontend/.env.local — run: ./scripts/sync-dev-env.sh"
fi

echo ""
if lsof -ti:"$UI_PORT" >/dev/null 2>&1; then
  echo "OK  UI port $UI_PORT in use (npm run dev likely running)"
else
  echo "—   UI port $UI_PORT free — run: cd frontend && npm run dev"
fi

echo ""
if [ "$ok" = 1 ]; then
  echo "Open: ${UI_URL}/interview"
else
  exit 1
fi
