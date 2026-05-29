#!/usr/bin/env bash
# Load dev ports: runtime (dynamic) overrides config/dev-ports.json defaults.
PORTS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULTS_FILE="$PORTS_ROOT/config/dev-ports.json"
RUNTIME_FILE="$PORTS_ROOT/config/runtime-ports.json"

if [ ! -f "$DEFAULTS_FILE" ]; then
  echo "Missing $DEFAULTS_FILE" >&2
  exit 1
fi

# Ensure runtime ports exist (picks free ports if defaults are taken)
if [ ! -f "$RUNTIME_FILE" ]; then
  "$PORTS_ROOT/scripts/allocate-ports.sh"
fi

_read_merged() {
  python3 -c "
import json
from pathlib import Path
root = Path('$PORTS_ROOT')
defaults = json.load(open(root / 'config/dev-ports.json'))
runtime = json.load(open(root / 'config/runtime-ports.json'))
merged = {**defaults, **runtime}
print(merged['$1'])
"
}

DEV_HOST="$(_read_merged host)"
AFFINE_API_PORT="$(_read_merged affineApiPort)"
UI_PORT="$(_read_merged uiPort)"
AFFINE_API_TARGET="http://${DEV_HOST}:${AFFINE_API_PORT}"
UI_URL="http://localhost:${UI_PORT}"
