#!/usr/bin/env bash
# Load fixed dev ports from config/dev-ports.json (do not hardcode ports elsewhere).
PORTS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORTS_FILE="$PORTS_ROOT/config/dev-ports.json"

if [ ! -f "$PORTS_FILE" ]; then
  echo "Missing $PORTS_FILE" >&2
  exit 1
fi

_read_json() {
  python3 -c "import json; print(json.load(open('$PORTS_FILE'))['$1'])"
}

DEV_HOST="$(_read_json host)"
AFFINE_API_PORT="$(_read_json affineApiPort)"
MOCK_API_PORT="$(_read_json mockApiPort)"
UI_PORT="$(_read_json uiPort)"
AFFINE_API_TARGET="http://${DEV_HOST}:${AFFINE_API_PORT}"
MOCK_API_TARGET="http://${DEV_HOST}:${MOCK_API_PORT}"
UI_URL="http://localhost:${UI_PORT}"
