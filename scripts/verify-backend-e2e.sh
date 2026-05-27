#!/usr/bin/env bash
# End-to-end backend verification for AFFINE.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=ports.sh
source "$(cd "$(dirname "$0")" && pwd)/ports.sh"
API_BASE="$AFFINE_API_TARGET"

echo "=== AFFINE backend E2E check ==="
echo "API: $API_BASE (config/dev-ports.json)"
echo ""

if ! curl -sf -m 5 "$API_BASE/health" >/dev/null 2>&1; then
  echo "FAIL: API not running. Start with:"
  echo "  ./scripts/start-backend.sh"
  exit 1
fi

echo "1. Health"
curl -s "$API_BASE/health"
echo ""
echo ""

echo "2. Create session"
RESP=$(curl -sf -m 120 -X POST "$API_BASE/api/sessions" \
  -H "Content-Type: application/json" \
  -d '{"problem_statement":"We need a simple loan review assistant that reads applications, checks policy, and sends unclear cases to a human reviewer."}')
echo "$RESP" | python3 -m json.tool 2>/dev/null | head -30 || echo "$RESP"
SID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['session']['id'])" 2>/dev/null || true)
echo ""
if [ -z "$SID" ]; then
  echo "FAIL: could not parse session id"
  exit 1
fi
echo "Session id: $SID"
echo ""

SESSION_FILE="$ROOT/backend/data/sessions/${SID}.json"
if [ -f "$SESSION_FILE" ]; then
  echo "3. Local session file exists: $SESSION_FILE"
else
  echo "3. Session file not on disk (OK if using Azure Blob only)"
fi
echo ""

echo "4. List launchpad workflows"
curl -s "$API_BASE/api/launchpad/workflows" | python3 -m json.tool 2>/dev/null | head -20
echo ""

echo "OK"
echo "UI: frontend/.env.local → AFFINE_API_TARGET=$API_BASE"
echo "Run: cd frontend && npm run dev → ${UI_URL}/interview"
