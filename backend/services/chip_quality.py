"""Quality gate and merge helpers for interview answer chips."""

from __future__ import annotations

import re

OTHER_CHIP = "Other / describe in chat"

_TOKEN_RE = re.compile(r"[a-z0-9]{3,}")

MIN_CHIP_WORDS = 2
MAX_CHIP_CHARS = 160
MIN_MERGED_CHIPS = 2
JACCARD_DUPLICATE_THRESHOLD = 0.72


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall((text or "").lower()))


def _word_count(text: str) -> int:
    return len([w for w in (text or "").split() if w.strip()])


def jaccard_similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def is_other_chip(chip: str) -> bool:
    return chip.strip().lower() == OTHER_CHIP.lower()


def normalize_chip_text(chip: str) -> str:
    return " ".join((chip or "").split())


def chip_passes_quality_gate(
    chip: str,
    *,
    input_name: str = "",
    agent_summary: str = "",
    min_words: int = MIN_CHIP_WORDS,
) -> bool:
    text = normalize_chip_text(chip)
    if not text or is_other_chip(text):
        return False
    if len(text) > MAX_CHIP_CHARS:
        return False
    if _word_count(text) < min_words:
        return False

    domain = _tokens(f"{input_name} {agent_summary}")
    chip_t = _tokens(text)
    if domain and chip_t and not (domain & chip_t):
        # Allow catalog-style chips that use plain English without technical tokens.
        if not any(w in text.lower() for w in ("use ", "send ", "upload", "review", "default", "manual")):
            return False
    return True


def dedupe_chips(chips: list[str]) -> list[str]:
    out: list[str] = []
    for chip in chips:
        text = normalize_chip_text(chip)
        if not text or is_other_chip(text):
            continue
        if any(jaccard_similarity(text, kept) >= JACCARD_DUPLICATE_THRESHOLD for kept in out):
            continue
        out.append(text)
    return out


def gate_chip_list(
    chips: list[str],
    *,
    input_name: str = "",
    agent_summary: str = "",
) -> list[str]:
    gated: list[str] = []
    for chip in chips:
        if chip_passes_quality_gate(
            chip,
            input_name=input_name,
            agent_summary=agent_summary,
        ):
            gated.append(normalize_chip_text(chip))
    return dedupe_chips(gated)


def pick_suggested_chip(
    chips: list[str],
    *,
    query: str = "",
    rank_hint: float = 0.0,
) -> str | None:
    """Best chip for UI highlight — never Other."""
    core = [c for c in chips if not is_other_chip(c)]
    if not core:
        return None
    if rank_hint >= 70 and core:
        return core[0]
    if query.strip():
        q_tokens = _tokens(query)
        scored = sorted(
            core,
            key=lambda c: len(_tokens(c) & q_tokens),
            reverse=True,
        )
        if scored and (_tokens(scored[0]) & q_tokens):
            return scored[0]
    return core[0]


def merge_and_gate_chips(
    *,
    deterministic: list[str] | None = None,
    catalog: list[str] | None = None,
    contextual: list[str] | None = None,
    llm: list[str] | None = None,
    input_name: str = "",
    agent_summary: str = "",
    limit: int = 5,
) -> list[str]:
    """
    Merge tier order: deterministic → catalog → contextual → llm, then quality gate.
    Always ends with Other / describe in chat.
    """
    merged: list[str] = []
    seen: set[str] = set()

    for source in (deterministic or [], catalog or [], contextual or [], llm or []):
        for chip in source:
            if is_other_chip(chip):
                continue
            key = chip.lower().strip()
            if key in seen:
                continue
            seen.add(key)
            merged.append(normalize_chip_text(chip))

    gated = gate_chip_list(
        merged,
        input_name=input_name,
        agent_summary=agent_summary,
    )

    if len(gated) < MIN_MERGED_CHIPS and deterministic:
        for chip in deterministic:
            if is_other_chip(chip):
                continue
            text = normalize_chip_text(chip)
            if text and text not in gated:
                gated.append(text)
            if len(gated) >= MIN_MERGED_CHIPS:
                break

    if len(gated) < MIN_MERGED_CHIPS:
        fallback = gate_chip_list(
            [
                f"Use the standard setup for {input_name or 'this input'}",
                "Configure per case with analyst review",
            ],
            input_name=input_name,
            agent_summary=agent_summary,
        )
        for chip in fallback:
            if chip not in gated:
                gated.append(chip)

    return gated[:limit] + [OTHER_CHIP]
