"""Tests for interview chip quality gate."""

from services.chip_quality import (
    OTHER_CHIP,
    gate_chip_list,
    is_other_chip,
    jaccard_similarity,
    merge_and_gate_chips,
    pick_suggested_chip,
)


def test_jaccard_detects_near_duplicates():
    assert jaccard_similarity("Use PDF uploads", "Use PDF document uploads") > 0.5


def test_gate_drops_short_chips():
    gated = gate_chip_list(
        ["PDF", "Use uploaded PDF and DOCX filings for extraction"],
        input_name="document format",
        agent_summary="Extracts entities from filings",
    )
    assert len(gated) == 1
    assert "PDF" not in gated[0] or "uploaded" in gated[0].lower()


def test_merge_always_includes_other():
    merged = merge_and_gate_chips(
        deterministic=["Use our current KYC policy JSON file"],
        input_name="policy json",
        agent_summary="Validates KYC policy fields",
    )
    assert merged[-1] == OTHER_CHIP
    assert len([c for c in merged if not is_other_chip(c)]) >= 2


def test_pick_suggested_never_other():
    chips = ["Option A for analysts", "Option B automatic", OTHER_CHIP]
    assert pick_suggested_chip(chips) == "Option A for analysts"
