#!/usr/bin/env bash
# Stop stuck AFFINE dev servers (uvicorn + vite) on common ports.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORTS=(3001 8003 8004 5173 5174 5175)
for port in "${PORTS[@]}"; do
  pids=$(lsof -ti:"$port" 2>/dev/null || true)
  if [ -n "$pids" ]; then
    echo "Killing port $port (PIDs: $pids)"
    kill -9 $pids 2>/dev/null || true
  fi
done
echo "Done. Ports ${PORTS[*]} should be free."
bash "$ROOT/scripts/clean-sessions.sh"
echo "UI: open http://localhost:5173/?fresh=1 to skip restoring the last interview from localStorage."
echo "If you suspended jobs with Ctrl+Z, run: jobs   then: kill %1 %2 ..."
