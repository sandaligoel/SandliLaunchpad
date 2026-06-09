"""Deterministic clarifying questions before the agent workflow interview."""

from __future__ import annotations

import logging
from typing import Optional

from config import Settings
from schemas.architecture_spec import ClarifyingQuestionItem
from services.catalog_chip_suggestions import (
    OTHER_CHIP,
    _integration_chips_from_catalog,
    _top_project_context,
)

logger = logging.getLogger(__name__)

CLARIFYING_FIELD_PREFIX = "clarifying:"


def clarifying_field_key(question_id: str) -> str:
    return f"{CLARIFYING_FIELD_PREFIX}{question_id}"


def is_clarifying_field_key(field_key: Optional[str]) -> bool:
    return bool(field_key and field_key.startswith(CLARIFYING_FIELD_PREFIX))


def _detect_problem_domain(query: str) -> str:
    q = query.lower()
    if any(
        w in q
        for w in (
            "chatbot",
            "chat bot",
            " copilot",
            "copilot ",
            "conversation",
            "assistant",
            " bot",
            "bot ",
            "build a bot",
        )
    ):
        return "chat"
    if any(w in q for w in ("image", "photo", "shelf", "planogram", "video", "vision")):
        return "vision"
    if any(w in q for w in ("pdf", "kyc", "document", "filing", "compliance", "onboarding")):
        return "documents"
    if any(w in q for w in ("fashion", "garment", "try-on", "vto", "retail")):
        return "retail"
    return "general"


def _deterministic_clarifying_questions(query: str) -> list[ClarifyingQuestionItem]:
    """Same problem statement always yields the same three scoping questions."""
    domain = _detect_problem_domain(query)

    if domain == "chat":
        q1 = (
            "What inputs will the chatbot receive — user messages only, "
            "uploaded files, or both?"
        )
        q1_why = "Input channels determine ingestion agents and context handling."
    elif domain == "vision":
        q1 = (
            "What visual inputs will this workflow use — shelf photos, "
            "planogram images, or product reference photos?"
        )
        q1_why = "Image type selects the vision detection and search agents."
    elif domain == "documents":
        q1 = (
            "What document types will users upload — PDF, DOCX, TXT, or a mix?"
        )
        q1_why = "Document format drives extraction and validation agents."
    elif domain == "retail":
        q1 = (
            "What reference inputs are required — person photos, product images, "
            "or catalog metadata?"
        )
        q1_why = "Reference inputs define the vision and composition pipeline."
    else:
        q1 = (
            "What is the primary input for this workflow — documents, images, "
            "data feeds, or chat messages?"
        )
        q1_why = "Input type determines which ingestion agents are selected."

    q2 = (
        "When should a human review step be required — always, only on "
        "exceptions, or never?"
    )
    q2_why = "Review policy sets HITL gates in the architecture."

    q3 = (
        "Which systems must this workflow connect to for inputs and outputs — "
        "email, CRM, database, or standalone only?"
    )
    q3_why = "Integrations define data interfaces between agents."

    return [
        ClarifyingQuestionItem(id="q1", question=q1, why_it_matters=q1_why),
        ClarifyingQuestionItem(id="q2", question=q2, why_it_matters=q2_why),
        ClarifyingQuestionItem(id="q3", question=q3, why_it_matters=q3_why),
    ]


def chips_for_clarifying_question(
    question_id: str,
    query: str,
    settings: Settings,
    *,
    preferred_agent_ids: list[str] | None = None,
) -> list[str]:
    """Stable, question-specific follow-up chips (not shared across clarifying questions)."""
    domain = _detect_problem_domain(query)
    qid = (question_id or "").strip().lower()

    if qid == "q1":
        if domain == "chat":
            core = [
                "User chat messages only",
                "Chat messages plus uploaded PDF or image files",
                "API messages from a client application",
            ]
        elif domain == "vision":
            core = [
                "Retail shelf or planogram photos (JPEG/PNG)",
                "Product reference images only",
                "Mixed shelf photos and PDF planogram specs",
            ]
        elif domain == "documents":
            core = [
                "PDF corporate filings only",
                "PDF and DOCX mixed uploads",
                "Plain text exports from a case management system",
            ]
        elif domain == "retail":
            core = [
                "Person photo plus garment reference images",
                "Product catalog images only",
                "Person photo with up to eight accessory images",
            ]
        else:
            core = [
                "Uploaded documents (PDF/DOCX/TXT)",
                "Images or photos",
                "Database or API records",
            ]
        return core[:4] + [OTHER_CHIP]

    if qid == "q2":
        return [
            "A person reviews every output before it is used",
            "Only exceptions or low-confidence cases need review",
            "Fully automatic — no regular human review",
            OTHER_CHIP,
        ]

    if qid == "q3":
        _project, agents, _score = _top_project_context(
            query, settings, preferred_agent_ids=preferred_agent_ids
        )
        core = _integration_chips_from_catalog(agents)[:3]
        if not core:
            core = [
                "Email for intake and notifications",
                "Corporate database or CRM system",
                "Standalone — no external integrations yet",
            ]
        return core[:4] + [OTHER_CHIP]

    return [
        "Use the closest standard option for this workflow",
        "Configure per case with analyst review",
        OTHER_CHIP,
    ]


def generate_clarifying_questions(
    raw_query: str,
    settings: Settings,
    client=None,
    *,
    catalog_context: str = "",
) -> list[ClarifyingQuestionItem]:
    """
    Return three deterministic scoping questions for the problem statement.

    Same query always produces the same questions (no LLM variance).
    """
    del settings, client, catalog_context
    statement = raw_query.strip()
    if len(statement) < 10:
        raise ValueError("Problem statement must be at least 10 characters")
    questions = _deterministic_clarifying_questions(statement)
    logger.info(
        "Clarifying questions (deterministic, domain=%s): %d",
        _detect_problem_domain(statement),
        len(questions),
    )
    return questions


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
