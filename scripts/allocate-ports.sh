#!/usr/bin/env bash
# Pick free ports near defaults and write config/runtime-ports.json (shared by backend + frontend).
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME="$ROOT/config/runtime-ports.json"
DEFAULTS="$ROOT/config/dev-ports.json"

export AFFINE_PORTS_ROOT="$ROOT"
python3 <<'PY'
import json
import os
import socket
from datetime import datetime, timezone
from pathlib import Path

root = Path(os.environ["AFFINE_PORTS_ROOT"])
defaults = json.loads((root / "config/dev-ports.json").read_text())
runtime_path = root / "config/runtime-ports.json"

existing = {}
if runtime_path.is_file():
    try:
        existing = json.loads(runtime_path.read_text())
    except json.JSONDecodeError:
        existing = {}

host = defaults.get("host", "127.0.0.1")


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def affine_health_ok(port: int) -> bool:
    import urllib.error
    import urllib.request

    url = f"http://{host}:{port}/health"
    try:
        with urllib.request.urlopen(url, timeout=1.5) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def pick_port(key: str, env_var: str) -> int:
    base = int(existing.get(key) or os.environ.get(env_var) or defaults[key])
    if not port_free(base):
        if key == "affineApiPort" and affine_health_ok(base):
            return base
    else:
        return base
    for offset in range(1, 100):
        candidate = base + offset
        if port_free(candidate):
            return candidate
    raise SystemExit(f"No free port found near {base} for {key}")


ports = {
    "host": host,
    "affineApiPort": pick_port("affineApiPort", "AFFINE_API_PORT"),
    "uiPort": pick_port("uiPort", "UI_PORT"),
    "updatedAt": datetime.now(timezone.utc).isoformat(),
}

runtime_path.parent.mkdir(parents=True, exist_ok=True)
runtime_path.write_text(json.dumps(ports, indent=2) + "\n")

print(f"Runtime ports → {runtime_path}")
print(f"  Backend  http://{host}:{ports['affineApiPort']}")
print(f"  Frontend http://localhost:{ports['uiPort']}")
PY
