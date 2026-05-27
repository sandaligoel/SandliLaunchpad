#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=ports.sh
source "$ROOT/scripts/ports.sh"
API_PORT="$AFFINE_API_PORT"

cd "$ROOT/backend"
if [ -f .venv/bin/uvicorn ] && grep -q "agent_catalog/.venv" .venv/bin/uvicorn 2>/dev/null; then
  echo "Stale .venv (points at removed agent_catalog/). Recreate:"
  echo "  cd backend && rm -rf .venv && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi
if [ ! -d .venv ]; then
  echo "Missing .venv — run: python3 -m venv .venv && pip install -r requirements.txt"
  exit 1
fi
if [ ! -f .env ]; then
  echo "Missing .env — run: cp .env.example .env"
  exit 1
fi

source .venv/bin/activate
# Do not `source .env` — semicolons in connection strings break bash. Python loads .env via dotenv.

echo "AFFINE API → ${AFFINE_API_TARGET}/health"
echo "UI proxy target → ${AFFINE_API_TARGET} (config/dev-ports.json)"

PYTHONPATH=. python -c "
from dotenv import load_dotenv
load_dotenv('.env')
from services.data_storage import blob_storage_configured, get_storage_status
if not blob_storage_configured():
    print('Storage: LOCAL only — set AZURE_STORAGE_* in backend/.env')
else:
    import os
    acct = os.getenv('AZURE_STORAGE_ACCOUNT_NAME', '')
    ctr = os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'agentic-launchpad')
    print(f'Storage: Azure Blob ({acct} / {ctr})')
    s = get_storage_status()
    print('  reachable:', s.get('reachable'), '| sessions:', s.get('session_blob_count', 'n/a'))
    if s.get('error'):
        print('  error:', s['error'])
" 2>/dev/null || echo "Storage: (could not check — run pip install -r requirements.txt)"

exec uvicorn api.main:app --reload --host 127.0.0.1 --port "$API_PORT"
