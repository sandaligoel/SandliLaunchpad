#!/usr/bin/env bash
# Alias — use scripts/start-mock-api.sh
exec "$(cd "$(dirname "$0")" && pwd)/start-mock-api.sh" "$@"
