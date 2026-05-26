#!/usr/bin/env bash
# Test connectivity to deployed AFFINE API.
# Usage: ./scripts/test-azure-api.sh https://your-api.azurecontainerapps.io
set -e
BASE="${1:?Pass API base URL, e.g. https://affine-agent-api.xxx.azurecontainerapps.io}"
BASE="${BASE%/}"
echo "Health: $BASE/health"
curl -sf "$BASE/health" | head -c 500
echo ""
echo "OK — set AFFINE_API_TARGET=$BASE in agentforge-ui/.env.local and restart npm run dev"
