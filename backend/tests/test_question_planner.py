"""Gap-driven question planner."""

from server import DiscoveryAnswer, DiscoveryState
from server import (
    extract_knowns,
    extract_unknowns,
    plan_discovery_question,
    rank_unknowns,
    understand_goal,
)


def test_vto_workflow_asks_domain_first():
    goal = understand_goal("Build a virtual try-on workflow")
    state = DiscoveryState(original_request="Build a virtual try-on workflow")
    knowns = extract_knowns(state, goal)
    unknowns = extract_unknowns(goal, knowns)
    ranked = rank_unknowns(goal, knowns, unknowns)

    assert ranked
    assert ranked[0].key == "workflow_domain"
    assert ranked[0].composite_score >= ranked[1].composite_score


def test_after_domain_answer_next_is_not_domain():
    state = DiscoveryState(
        original_request="Build a virtual try-on workflow",
        covered_topics=["workflow_domain"],
    )
    state.answers = [
        DiscoveryAnswer(
            question_id="q1",
            question="Which domain?",
            answer="Fashion and apparel",
            topic="workflow_domain",
        )
    ]
    result = plan_discovery_question(state)
    assert result.best is not None
    assert result.best.key != "workflow_domain"


def test_planner_pipeline_returns_question():
    state = DiscoveryState(original_request="Build a virtual try-on workflow")
    result = plan_discovery_question(state)
    assert result.best is not None
    assert result.best.key == "workflow_domain"
