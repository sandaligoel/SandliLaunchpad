#!/usr/bin/env bash
# End-to-end backend verification for AFFINE agent_catalog.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_PORT="${AFFINE_API_PORT:-8003}"
API_BASE="http://127.0.0.1:${API_PORT}"

echo "=== AFFINE backend E2E check ==="
echo "API: $API_BASE"
echo ""

# Try 8003 then 8004 if health fails
if ! curl -sf -m 5 "$API_BASE/health" >/dev/null 2>&1; then
  if curl -sf -m 5 "http://127.0.0.1:8004/health" >/dev/null 2>&1; then
    API_PORT=8004
    API_BASE="http://127.0.0.1:8004"
    echo "Note: API is on port 8004 — set AFFINE_API_TARGET=$API_BASE in agentforge-ui/.env.local"
  else
    echo "FAIL: API not running. Start with:"
    echo "  cd agent_catalog && source .venv/bin/activate"
    echo "  uvicorn api.main:app --reload --host 127.0.0.1 --port 8003"
    exit 1
  fi
fi

echo "1. Health"
curl -s "$API_BASE/health"
echo ""
echo ""

echo "2. Start interview session"
RESP=$(curl -sf -m 120 -X POST "$API_BASE/api/sessions" \
  -H "Content-Type: application/json" \
  -d '{"problem_statement":"We need a simple agent to triage customer support emails and escalate urgent cases to a human reviewer."}')
SID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['session']['id'])" 2>/dev/null || true)
if [ -z "$SID" ]; then
  echo "FAIL: Could not start session"
  echo "$RESP" | head -c 500
  exit 1
fi
echo "   session id: $SID"
echo ""

echo "3. Session file on disk"
SESSION_FILE="$ROOT/agent_catalog/data/sessions/${SID}.json"
if [ -f "$SESSION_FILE" ]; then
  echo "   OK: $SESSION_FILE"
  ls -la "$SESSION_FILE"
else
  echo "   WARN: file not found yet (may appear after first turn)"
fi
echo ""

echo "4. Reload session via API"
curl -sf -m 30 "$API_BASE/api/sessions/$SID" | python3 -c "
import sys, json
s = json.load(sys.stdin)['session']
print('   status:', s['spec']['status'])
print('   messages:', len(s.get('messages', [])))
"
echo ""

echo "=== All checks passed ==="
echo "UI: agentforge-ui/.env.local → AFFINE_API_TARGET=$API_BASE"
echo "Run: cd agentforge-ui && npm run dev → http://localhost:5173/interview"
