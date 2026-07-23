#!/usr/bin/env python3
"""Fail CI when placeholder implementations remain in application code."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

SCAN_DIRS = [
    REPO_ROOT / "agent_library" / "build",
    REPO_ROOT / "agent_runtime",
    REPO_ROOT,
]

SCAN_FILES = [
    REPO_ROOT / "main.py",
    REPO_ROOT / "config.py",
    REPO_ROOT / "run_workflow.py",
]

SKIP_DIR_NAMES = {"tests", "__pycache__", ".venv", "reuse", "backend", "frontend", "docs"}
SKIP_FILE_NAMES = {"check_placeholders.py"}

FORBIDDEN_COMMENT = re.compile(r"\b(TODO|FIXME|XXX)\b")
FORBIDDEN_MOCK_IMPORT = re.compile(r"\b(unittest\.mock|from mock import|@patch)\b")
FORBIDDEN_FAKE_DATA = re.compile(
    r"\b(fake_response|canned_response|dummy_data|mock_response|placeholder_value)\b",
    re.IGNORECASE,
)


def _iter_python_files() -> list[Path]:
    files: list[Path] = []
    for scan_dir in SCAN_DIRS:
        if not scan_dir.exists():
            continue
        if scan_dir.is_file() and scan_dir.suffix == ".py":
            files.append(scan_dir)
            continue
        for path in scan_dir.rglob("*.py"):
            if any(part in SKIP_DIR_NAMES for part in path.parts):
                continue
            if path.name in SKIP_FILE_NAMES:
                continue
            files.append(path)
    for path in SCAN_FILES:
        if path.exists() and path not in files:
            files.append(path)
    return sorted(set(files))


def _check_bare_pass(path: Path, tree: ast.AST, violations: list[str]) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            body = node.body
            if len(body) == 1 and isinstance(body[0], ast.Pass):
                violations.append(f"{path}: function '{node.name}' has bare pass body")


def _scan_file(path: Path) -> list[str]:
    rel = path.relative_to(REPO_ROOT)
    text = path.read_text(encoding="utf-8", errors="replace")
    violations: list[str] = []

    if "raise NotImplementedError" in text and "agent_library/build" in str(path):
        violations.append(f"{rel}: contains raise NotImplementedError")

    for index, line in enumerate(text.splitlines(), start=1):
        if FORBIDDEN_COMMENT.search(line):
            violations.append(f"{rel}:{index}: forbidden comment marker")
        if FORBIDDEN_MOCK_IMPORT.search(line):
            violations.append(f"{rel}:{index}: mock import outside tests")
        if FORBIDDEN_FAKE_DATA.search(line):
            violations.append(f"{rel}:{index}: fake data marker")

    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        violations.append(f"{rel}: syntax error — {exc}")
        return violations

    _check_bare_pass(path, tree, violations)
    return violations


def main() -> int:
    all_violations: list[str] = []
    for path in _iter_python_files():
        all_violations.extend(_scan_file(path))

    if all_violations:
        print(f"Found {len(all_violations)} placeholder violation(s):", file=sys.stderr)
        for violation in all_violations:
            print(f"  - {violation}", file=sys.stderr)
        return 1

    print("No placeholder violations found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
