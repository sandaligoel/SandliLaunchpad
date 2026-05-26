#!/usr/bin/env bash
# Mock API for AgentForge UI (workflows, agents, dashboard). Port 3001.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/agentforge-mock-api"
if [ ! -d node_modules ]; then
  npm install
fi
exec npm run dev
