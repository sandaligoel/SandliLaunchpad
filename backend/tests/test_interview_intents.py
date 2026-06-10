"""Problem-statement revision intent detection."""

from server import (
    extract_revised_problem_statement,
    is_change_problem_statement_intent,
    is_problem_revision_submission,
    is_revision_help_question,
    looks_like_problem_statement,
    should_begin_workflow_building,
)


def test_detect_change_problem_intent():
    assert is_change_problem_statement_intent("i want to change the problem statement")
    assert is_change_problem_statement_intent("I want to change the problem statement")
    assert is_change_problem_statement_intent("edit my original prompt")
    assert not is_change_problem_statement_intent(
        "Retail shelf or planogram photos (JPEG/PNG)"
    )


def test_change_problem_not_treated_as_help():
    from server import is_general_help_request

    text = "I want to change the problem statement"
    assert is_change_problem_statement_intent(text)
    assert not is_general_help_request(text)


def test_questions_stay_in_open_chat():
    assert not should_begin_workflow_building("what is HITL?")
    assert not should_begin_workflow_building("what problem statement can i give?")


def test_workflow_description_triggers_builder():
    text = (
        "Build an agentic workflow that accepts invoices, extracts fields, "
        "validates against POs, and routes exceptions to finance reviewers."
    )
    assert should_begin_workflow_building(text)


def test_help_question_not_treated_as_problem_statement():
    assert is_revision_help_question("what problem statement can i give?")
    assert not looks_like_problem_statement("what problem statement can i give?")
    assert extract_revised_problem_statement("what problem statement can i give?") is None


def test_chatbot_goal_counts_as_problem_statement():
    text = "build a chatbot for structured and unstructured data"
    assert looks_like_problem_statement(text)
    assert is_problem_revision_submission(text)
    assert should_begin_workflow_building(text)


def test_extract_inline_revision():
    text = (
        "Change problem statement: Build a chatbot for retail analytics "
        "with human review before publishing."
    )
    body = extract_revised_problem_statement(text)
    assert body is not None
    assert "chatbot" in body.lower()
