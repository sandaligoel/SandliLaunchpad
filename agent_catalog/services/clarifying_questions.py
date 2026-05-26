"""Generate three problem-specific clarifying questions before spec interview."""

from __future__ import annotations

import json
import logging
from typing import Optional

from openai import AzureOpenAI
from pydantic import ValidationError

from config import Settings
from schemas.architecture_spec import ClarifyingQuestionItem
from services.llm import call_llm, load_prompt, make_client, strip_json_fences

logger = logging.getLogger(__name__)

CLARIFYING_FIELD_PREFIX = "clarifying:"


def clarifying_field_key(question_id: str) -> str:
    return f"{CLARIFYING_FIELD_PREFIX}{question_id}"


def is_clarifying_field_key(field_key: Optional[str]) -> bool:
    return bool(field_key and field_key.startswith(CLARIFYING_FIELD_PREFIX))


def generate_clarifying_questions(
    raw_query: str,
    settings: Settings,
    client: AzureOpenAI | None = None,
) -> list[ClarifyingQuestionItem]:
    """
    Ask the LLM for exactly three architecture-shaping clarifying questions.

    Raises:
        ValueError: On empty query or invalid LLM output.
    """
    statement = raw_query.strip()
    if len(statement) < 10:
        raise ValueError("Problem statement must be at least 10 characters")

    if client is None:
        client = make_client(settings)

    system = load_prompt("clarifying_questions.txt").replace("{raw_query}", statement)
    user = "Return the JSON object with exactly three questions."

    raw = call_llm(
        client,
        settings,
        system,
        user,
        json_mode=True,
        temperature=0.35,
    )
    try:
        parsed = json.loads(strip_json_fences(raw))
        items = parsed.get("questions") or []
        questions: list[ClarifyingQuestionItem] = []
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            qid = str(item.get("id") or f"q{i + 1}").strip()
            qtext = str(item.get("question") or "").strip()
            why = str(item.get("why_it_matters") or "").strip()
            if not qtext:
                continue
            questions.append(
                ClarifyingQuestionItem(id=qid, question=qtext, why_it_matters=why)
            )
        if len(questions) != 3:
            raise ValueError(
                f"Expected exactly 3 clarifying questions, got {len(questions)}"
            )
        return questions
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.error("Clarifying questions parse failed: %s", exc)
        raise ValueError("Could not parse clarifying questions from model") from exc


def format_clarifying_summary(
    questions: list[ClarifyingQuestionItem],
    answers: dict[str, str],
) -> str:
    """Build text block injected into spec context after clarifying phase."""
    lines = ["Business clarifications (pre-architecture):"]
    for q in questions:
        ans = answers.get(q.id, "").strip() or "(no answer)"
        lines.append(f"- Q ({q.id}): {q.question}")
        lines.append(f"  A: {ans}")
        if q.why_it_matters:
            lines.append(f"  (shapes architecture because: {q.why_it_matters})")
    return "\n".join(lines)


def pending_clarifying_question(
    questions: list[ClarifyingQuestionItem],
    answers: dict[str, str],
) -> Optional[ClarifyingQuestionItem]:
    """Return the next clarifying question not yet answered."""
    for q in questions:
        if q.id not in answers or not answers[q.id].strip():
            return q
    return None
