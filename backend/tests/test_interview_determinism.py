"""Interview questions and chips are stable for the same problem statement."""

from server import (
    _deterministic_clarifying_questions,
    chips_for_clarifying_question,
    generate_clarifying_questions,
)
from server import (
    _build_questions_deterministic,
    _match_agents,
)
from server import _load_catalog
from server import get_settings


PROBLEM = (
    "Build a chatbot for saturated and unsaturated data analysis "
    "with human review before publishing results."
)

DATA_BOT = "build a bot for saturated and unsaturated data"


def test_clarifying_questions_stable_for_same_query():
    a = _deterministic_clarifying_questions(PROBLEM)
    b = _deterministic_clarifying_questions(PROBLEM)
    assert [q.question for q in a] == [q.question for q in b]
    assert [q.id for q in a] == ["q1", "q2", "q3"]


def test_clarifying_chips_differ_by_question_id():
    settings = get_settings()
    q1 = chips_for_clarifying_question("q1", PROBLEM, settings)
    q2 = chips_for_clarifying_question("q2", PROBLEM, settings)
    q3 = chips_for_clarifying_question("q3", PROBLEM, settings)
    assert q1 != q2
    assert q2 != q3
    assert q1 == chips_for_clarifying_question("q1", PROBLEM, settings)


def test_agent_questions_stable_for_same_query():
    settings = get_settings()
    catalog = _load_catalog(settings)
    agents = _match_agents(PROBLEM, catalog)
    q1 = _build_questions_deterministic(agents, PROBLEM, catalog)
    q2 = _build_questions_deterministic(agents, PROBLEM, catalog)
    assert [(x.agent_id, x.input_name, x.question) for x in q1] == [
        (x.agent_id, x.input_name, x.question) for x in q2
    ]
    assert [x.chips for x in q1] == [x.chips for x in q2]


def test_generate_clarifying_questions_public_api():
    settings = get_settings()
    first = generate_clarifying_questions(PROBLEM, settings)
    second = generate_clarifying_questions(PROBLEM, settings)
    assert len(first) == 3
    assert first == second


def test_data_bot_pins_quin_and_eryl():
    settings = get_settings()
    catalog = _load_catalog(settings)
    matched = _match_agents(DATA_BOT, catalog, limit=5)
    names = [a.name for a in matched]
    assert "Quin SQL Agent Chain" in names
    assert "Eryl Semantic RAG Agent Chain" in names
    assert "Pipeline Intent Classifier" in names
