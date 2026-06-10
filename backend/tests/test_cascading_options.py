"""Cascading option generation from spec.json catalog rows."""

from server import get_settings
from server import generate_clarifying_options
from server import chips_for_clarifying_question


QUERY = (
    "Build an agentic workflow that accepts a person photo plus product images "
    "and generates a try-on composite with human review."
)


def test_q1_options_come_from_catalog_inputs():
    settings = get_settings()
    chips = chips_for_clarifying_question("q1", QUERY, settings)
    blob = " ".join(chips).lower()
    assert "other / describe" in blob
    assert len(chips) >= 2
    assert not any(
        phrase in blob
        for phrase in (
            "user chat messages only",
            "uploaded documents (pdf/docx/txt)",
            "retail shelf",
        )
    )


def test_q3_options_change_after_q1_selection():
    settings = get_settings()
    q1 = chips_for_clarifying_question("q1", QUERY, settings)
    pick = next(c for c in q1 if c.lower() != "other / describe in chat")

    before = generate_clarifying_options("q3", QUERY, settings)
    after = generate_clarifying_options(
        "q3",
        QUERY,
        settings,
        prior_answers={"q1": pick},
    )
    assert before.options != after.options or before.debug["stages"] != after.debug["stages"]
