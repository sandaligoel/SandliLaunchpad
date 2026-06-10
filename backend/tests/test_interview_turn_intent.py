"""Intent classification for scoping turns."""

from server import ArchitectureSpec, InterviewQuestion, InterviewSession
from server import TurnIntent, classify_turn_intent


def _session_with_question(question: str) -> InterviewSession:
    return InterviewSession(
        id="test",
        spec=ArchitectureSpec.empty(
            "Build an agentic workflow with person photo and product images for try-on."
        ),
        pending_question=InterviewQuestion(
            field_key="discovery:integrations_systems:q1",
            question=question,
            chips=["Shopify catalog", "Azure Blob Storage", "Other / describe in chat"],
        ),
    )


def test_explain_this_is_clarification_not_answer():
    session = _session_with_question("What systems does this workflow connect to?")
    assert (
        classify_turn_intent("Explain this", session)
        == TurnIntent.CLARIFICATION_REQUEST
    )


def test_chip_selection_is_answer():
    session = _session_with_question("What systems does this workflow connect to?")
    assert (
        classify_turn_intent("Azure Blob Storage", session) == TurnIntent.ANSWER
    )


def test_why_asking_is_clarification():
    session = _session_with_question("What systems does this workflow connect to?")
    assert (
        classify_turn_intent("Why are you asking this?", session)
        == TurnIntent.CLARIFICATION_REQUEST
    )
