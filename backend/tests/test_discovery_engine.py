"""State-driven discovery interview."""

from server import (
    discovery_to_clarifying_answers,
    initialize_discovery_state,
    plan_next_discovery_step,
)
from server import is_change_problem_statement_intent
from server import ArchitectureSpec, InterviewSession
from server import DiscoveryState, ExtractedRequirement, is_discovery_field_key


def test_discovery_field_keys():
    assert is_discovery_field_key("discovery:input_types:q1")
    assert not is_discovery_field_key("clarifying:q1")


def test_discovery_maps_to_clarifying_slots():
    state = DiscoveryState(
        original_request="Build a vision workflow with human review",
        extracted_requirements=[
            ExtractedRequirement(key="input_types", value="shelf photos", confidence=0.9),
            ExtractedRequirement(
                key="hitl_review_policy",
                value="Only exceptions",
                confidence=0.85,
            ),
        ],
    )
    mapping = discovery_to_clarifying_answers(state)
    assert "q1" in mapping
    assert "q2" in mapping


def test_change_problem_not_recorded_as_answer():
    assert is_change_problem_statement_intent("I want to change the problem statement")
