"""Dynamic, context-aware chip generation."""

from server import get_settings
from server import AgentRecord
from server import build_agent_input_chips
from server import generate_cascading_options
from server import _load_catalog
from server import chips_for_clarifying_question


def test_clarifying_q3_reflects_prior_answers():
    settings = get_settings()
    query = (
        "Build a chatbot for saturated and unsaturated data analysis "
        "with human review before publishing results."
    )
    prior = {
        "q1": "User chat messages plus uploaded PDF or image files",
        "q2": "Only exceptions or low-confidence cases need review",
    }
    chips = chips_for_clarifying_question(
        "q3",
        query,
        settings,
        prior_answers=prior,
    )
    blob = " ".join(chips).lower()
    assert "chat" in blob or "pdf" in blob or "upload" in blob
    assert "review" in blob or "exception" in blob


def test_agent_input_options_from_catalog_rows():
    settings = get_settings()
    catalog = _load_catalog(settings)
    agent = next(
        a
        for a in catalog.agents
        if any("PDF" in inp for inp in a.inputs)
    )
    input_name = next(inp for inp in agent.inputs if "PDF" in inp)
    from server import slugify

    result = generate_cascading_options(
        f"agent_input:{agent.id}:{slugify(input_name)}",
        "kyc document upload",
        settings,
        target_agent_id=agent.id,
        target_input_name=input_name,
    )
    assert result.options
    assert any("pdf" in c.lower() or "docx" in c.lower() for c in result.options)


def test_build_agent_input_chips_includes_contextual_tier():
    settings = get_settings()
    catalog = _load_catalog(settings)
    agent = catalog.agents[0]
    input_name = agent.inputs[0]
    chips, suggested, reason = build_agent_input_chips(
        agent,
        input_name,
        "corporate kyc onboarding with analyst review",
        settings,
        clarifying_answers={
            "q1": "Uploaded documents (PDF/DOCX/TXT)",
            "q2": "Only exceptions or low-confidence cases need review",
        },
        turn_index=2,
    )
    assert len(chips) >= 2
    assert any(not c.lower().startswith("other") for c in chips)
    assert suggested
    assert "earlier" in reason.lower() or "catalog" in reason.lower()
