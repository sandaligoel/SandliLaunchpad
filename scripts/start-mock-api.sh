#!/usr/bin/env bash
# Mock API for AgentForge UI (workflows, agents, dashboard).
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=ports.sh
source "$ROOT/scripts/ports.sh"
cd "$ROOT/mock-api"
export PORT="$MOCK_API_PORT"
echo "Mock API → ${MOCK_API_TARGET}/api"
if [ ! -d node_modules ]; then
  npm install
fi
exec npm run dev
