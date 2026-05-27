#!/usr/bin/env bash
# Alias — use scripts/start-backend.sh
exec "$(cd "$(dirname "$0")" && pwd)/start-backend.sh" "$@"
