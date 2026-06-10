#!/usr/bin/env python3
"""Upload existing backend/data/sessions/*.json into Azure Blob."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "backend"
sys.path.insert(0, str(CATALOG))

from dotenv import load_dotenv

load_dotenv(CATALOG / ".env")

from server import InterviewSession, blob_storage_configured, get_data_storage  # noqa: E402


def main() -> int:
    if not blob_storage_configured():
        print(
            "Set DATA_STORAGE_BACKEND=blob and AZURE_STORAGE_* in backend/.env",
            file=sys.stderr,
        )
        return 1

    sessions_dir = CATALOG / "data" / "sessions"
    if not sessions_dir.is_dir():
        print("No data/sessions directory found.")
        return 0

    storage = get_data_storage()
    uploaded = 0
    for path in sorted(sessions_dir.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            session = InterviewSession.model_validate(raw)
        except Exception as exc:
            print(f"Skip {path.name}: {exc}")
            continue
        key = f"sessions/{path.stem}.json"
        storage.write_json(key, json.loads(session.model_dump_json()))
        uploaded += 1
        print(f"Uploaded {path.name} -> launchpad/{key}")

    print(f"Done. {uploaded} session(s) uploaded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
