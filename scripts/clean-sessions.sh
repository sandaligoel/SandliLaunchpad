#!/usr/bin/env bash
# Remove all persisted interview sessions (disk + in-memory if API is running).
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SESSIONS_DIR="$ROOT/backend/data/sessions"

count=0
if [ -d "$SESSIONS_DIR" ]; then
  for f in "$SESSIONS_DIR"/*.json; do
    [ -e "$f" ] || continue
    rm -f "$f"
    count=$((count + 1))
  done
fi

echo "Removed $count session file(s) from backend/data/sessions/"
echo "Restart uvicorn to clear in-memory sessions, or they will repersist on next save."
echo "Open http://localhost:5173/?fresh=1 to clear the browser session id."
