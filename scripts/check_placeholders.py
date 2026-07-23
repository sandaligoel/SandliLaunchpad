#!/usr/bin/env python3
"""Scan application code for placeholder patterns that must not ship."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = [
    ROOT / "agent_library" / "build",
    ROOT / "agent_runtime",
    ROOT,
]
SCAN_FILES = [
    ROOT / "main.py",
    ROOT / "run_workflow.py",
    ROOT / "config.py",
    ROOT / "integrations",
]
IGNORED_DIRS = {"tests", ".git", ".venv", "__pycache__", "backend", "frontend", "docs", "config", "scripts"}

PATTERNS = {
    "todo_comment": re.compile(r"\b(TODO|FIXME|XXX)\b"),
    "not_implemented": re.compile(r"raise\s+NotImplementedError"),
    "unittest_mock": re.compile(r"\b(unittest\.mock|from\s+unittest\s+import\s+mock|@patch\b)"),
    "bare_pass": re.compile(r"^\s*pass\s*$"),
}


def iter_python_files() -> list[Path]:
    files: list[Path] = []
    for scan_dir in SCAN_DIRS:
        if not scan_dir.exists():
            continue
        if scan_dir.is_file():
            files.append(scan_dir)
            continue
        for path in scan_dir.rglob("*.py"):
            if any(part in IGNORED_DIRS for part in path.parts):
                continue
            files.append(path)
    for scan_path in SCAN_FILES:
        if scan_path.is_dir():
            files.extend(path for path in scan_path.rglob("*.py") if path.suffix == ".py")
        elif scan_path.exists() and scan_path.suffix == ".py":
            files.append(scan_path)
    return sorted(set(files))


def scan_file(path: Path) -> list[str]:
    violations: list[str] = []
    if "agent_library/reuse" in str(path):
        return violations
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{path}: unreadable ({exc})"]
    lines = content.splitlines()
    for line_number, line in enumerate(lines, start=1):
        for label, pattern in PATTERNS.items():
            if label == "bare_pass":
                if pattern.match(line) and _is_function_body_pass(lines, line_number - 1):
                    violations.append(f"{path}:{line_number}: bare pass in function body")
                continue
            if pattern.search(line):
                violations.append(f"{path}:{line_number}: matched {label}: {line.strip()}")
    return violations


def _is_function_body_pass(lines: list[str], index: int) -> bool:
    for previous in reversed(lines[:index]):
        stripped = previous.strip()
        if not stripped or stripped.startswith("#"):
            continue
        return stripped.endswith(":")
    return False


def main() -> int:
    violations: list[str] = []
    for path in iter_python_files():
        violations.extend(scan_file(path))
    if violations:
        print("Placeholder scan failed:")
        for violation in violations:
            print(violation)
        return 1
    print("Placeholder scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
