"""P3 chip tier trigger tests (no live LLM)."""

from server import MIN_TIER_CHIPS_BEFORE_LLM, _tier12_gated_count
from server import is_other_chip


def test_tier12_threshold_constant():
    assert MIN_TIER_CHIPS_BEFORE_LLM == 3


def test_tier12_count_with_rich_deterministic():
    n = _tier12_gated_count(
        deterministic=[
            "Use uploaded PDF and DOCX corporate filings for entity extraction",
            "Accept plain text exports from the case management system",
        ],
        catalog=[],
        contextual=[],
        input_name="PDF/TXT/DOCX document text",
        agent_summary="Extracts entities from corporate KYC documents",
    )
    assert n >= 2


def test_tier12_count_thin_catalog_triggers_p3_path():
    n = _tier12_gated_count(
        deterministic=[],
        catalog=[],
        contextual=[],
        input_name="obscure_internal_flag_xyz",
        agent_summary="Internal utility step",
    )
    assert n < MIN_TIER_CHIPS_BEFORE_LLM
