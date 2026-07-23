#!/usr/bin/env python3
"""Scan application code for placeholders, mocks, and incomplete implementations."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCAN_DIRS = [
    ROOT / "main.py",
    ROOT / "config.py",
    ROOT / "run_workflow.py",
    ROOT / "agent_runtime",
    ROOT / "integrations",
    ROOT / "agent_library" / "build",
    ROOT / "agent_library" / "base",
]

SKIP_DIR_NAMES = {"reuse", "tests", "__pycache__", ".git", ".venv", "venv"}

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("TODO/FIXME/XXX comment", re.compile(r"\b(TODO|FIXME|XXX)\b")),
    ("NotImplementedError in build agents", re.compile(r"raise\s+NotImplementedError")),
    ("unittest.mock outside tests", re.compile(r"\b(unittest\.mock|from\s+mock\s+import|@patch\b)")),
    ("bare pass statement", re.compile(r"^\s*pass\s*$")),
]

BUILD_AGENT_DIR = ROOT / "agent_library" / "build"


def iter_python_files() -> list[Path]:
    files: list[Path] = []
    for entry in SCAN_DIRS:
        if entry.is_file() and entry.suffix == ".py":
            files.append(entry)
        elif entry.is_dir():
            for path in entry.rglob("*.py"):
                if any(part in SKIP_DIR_NAMES for part in path.parts):
                    continue
                files.append(path)
    return sorted(set(files))


def is_allowed_pass(path: Path, line: str, lines: list[str], idx: int) -> bool:
    stripped = line.strip()
    if stripped != "pass":
        return False
    context = "\n".join(lines[max(0, idx - 3) : idx + 1])
    if "except " in context or "class " in context:
        return True
    if path.parent.name == "base":
        return True
    return False


def scan_file(path: Path) -> list[str]:
    findings: list[str] = []
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    rel = path.relative_to(ROOT)
    in_build = BUILD_AGENT_DIR in path.parents or path.parent == BUILD_AGENT_DIR

    for name, pattern in PATTERNS:
        if name.startswith("NotImplementedError") and not in_build:
            continue
        for idx, line in enumerate(lines, start=1):
            if name == "bare pass statement":
                if is_allowed_pass(path, line, lines, idx - 1):
                    continue
            if pattern.search(line):
                findings.append(f"{rel}:{idx}: {name}: {line.strip()}")
    return findings


def main() -> int:
    all_findings: list[str] = []
    for path in iter_python_files():
        all_findings.extend(scan_file(path))

    if all_findings:
        print("Placeholder / mock scan failed:")
        for item in all_findings:
            print(f"  - {item}")
        return 1

    print("Placeholder scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
