#!/usr/bin/env bash
# Stop stuck AFFINE dev servers (uvicorn + vite) on common ports.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=ports.sh
source "$(cd "$(dirname "$0")" && pwd)/ports.sh"
PORTS=("$AFFINE_API_PORT" 8003 8004 8005 5173 5174 5175 "$UI_PORT")
for port in "${PORTS[@]}"; do
  pids=$(lsof -ti:"$port" 2>/dev/null || true)
  if [ -n "$pids" ]; then
    echo "Killing port $port (PIDs: $pids)"
    kill -9 $pids 2>/dev/null || true
  fi
done
echo "Done. Ports ${PORTS[*]} should be free."
bash "$ROOT/scripts/clean-sessions.sh"
echo "UI: open ${UI_URL}/interview?fresh=1 for a new chat (no session in URL)."
echo "If you suspended jobs with Ctrl+Z, run: jobs   then: kill %1 %2 ..."
