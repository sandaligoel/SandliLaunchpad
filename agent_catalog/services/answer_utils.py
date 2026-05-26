"""Helpers for validating interview answers."""

from __future__ import annotations

import re

# Chip labels that must not be stored as field values — user should describe instead.
_CUSTOM_DESCRIBE_PATTERNS = (
    re.compile(r"^other\s*/\s*describe", re.I),
    re.compile(r"other.*describe.*chat", re.I),
    re.compile(r"^other\s*$", re.I),
    re.compile(r"^describe\s+in\s+chat$", re.I),
)


def is_custom_describe_placeholder(answer: str) -> bool:
    """True if the answer is only the 'Other / describe' chip text, not a real description."""
    text = answer.strip()
    if not text:
        return True
    if len(text) > 48:
        return False
    for pat in _CUSTOM_DESCRIBE_PATTERNS:
        if pat.search(text):
            return True
    return False
