"""Catalog-grounded chips for agent setup questions (spec.json inputs)."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass

from openai import AzureOpenAI

from config import Settings
from pipeline.spec_loader import CatalogLoadResult
from schemas.agent_record import AgentRecord
from schemas.architecture_spec import ArchitectureSpec, ChatMessage
from services.catalog_chip_suggestions import (
    OTHER_CHIP,
    _dedupe_chips,
    _normalize_chip,
    _rank_chips,
    contextual_chips_from_conversation,
)
from services.chip_quality import (
    gate_chip_list,
    is_other_chip,
    merge_and_gate_chips,
    pick_suggested_chip,
)
from services.catalog_interview_context import _load_catalog
from services.llm import call_llm, load_prompt, make_client, strip_json_fences

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]{3,}")
MIN_TIER_CHIPS_BEFORE_LLM = 3


def interview_uses_fast_chips() -> bool:
    """When true, skip per-question LLM chip generation (much faster chat turns)."""
    return os.getenv("INTERVIEW_FAST_CHIPS", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


@dataclass
class LlmChipGeneration:
    chips: list[str]
    suggested_index: int = 0
    grounding: list[str] | None = None


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall((text or "").lower()))


def catalog_values_for_input(
    catalog: CatalogLoadResult,
    agent: AgentRecord,
    input_name: str,
    *,
    limit: int = 4,
) -> list[str]:
    """Values seen in spec.json for the same input name (cross-agent patterns)."""
    target = _tokens(input_name)
    if not target:
        return []

    chips: list[str] = []
    for other in catalog.agents:
        if other.id == agent.id:
            continue
        if other.vertical != agent.vertical and agent.vertical != "Other":
            continue
        for inp in other.inputs:
            if _tokens(inp) & target or inp.lower() == input_name.lower():
                for out in other.outputs[:2]:
                    if out.strip():
                        chips.append(
                            _normalize_chip(
                                f"Same pattern as {other.name}: {out[:100]}"
                            )
                        )
                if other.function_summary:
                    chips.append(
                        _normalize_chip(
                            f"Align with {other.name} — {(other.function_summary or '')[:90]}"
                        )
                    )
                break
        if len(chips) >= limit:
            break
    return _dedupe_chips(chips)[:limit]


def _format_history(messages: list[ChatMessage] | None, limit: int = 8) -> str:
    if not messages:
        return "(none)"
    lines = [
        f"{m.role}: {m.content[:280]}"
        for m in messages[-limit:]
        if m.content and m.content.strip()
    ]
    return "\n".join(lines) if lines else "(none)"


def _format_prior_answers(spec: ArchitectureSpec | None) -> str:
    if not spec:
        return "(none)"
    parts: list[str] = []
    if spec.transcript_summary:
        parts.append(spec.transcript_summary.strip()[:1200])
    for key, field in spec.fields.items():
        if field.value and str(field.value).strip():
            parts.append(f"{key}: {str(field.value).strip()[:200]}")
    return "\n".join(parts) if parts else "(none)"


def _tier12_gated_count(
    *,
    deterministic: list[str],
    catalog: list[str],
    contextual: list[str],
    input_name: str,
    agent_summary: str,
) -> int:
    """How many quality-gated chips tiers 1–2 produce (before LLM)."""
    pre = merge_and_gate_chips(
        deterministic=deterministic,
        catalog=catalog,
        contextual=contextual,
        llm=[],
        input_name=input_name,
        agent_summary=agent_summary,
    )
    return len([c for c in pre if not is_other_chip(c)])


def generate_llm_chips_for_input(
    agent: AgentRecord,
    input_name: str,
    question: str,
    query: str,
    settings: Settings,
    client: AzureOpenAI,
    *,
    spec: ArchitectureSpec | None = None,
    messages: list[ChatMessage] | None = None,
    existing_chips: list[str] | None = None,
) -> LlmChipGeneration | None:
    """
  P3: Small dedicated LLM call for chip options when catalog tiers are thin.
    """
    existing = [
        c
        for c in (existing_chips or [])
        if c.strip() and not is_other_chip(c)
    ]
    system = (
        load_prompt("agent_input_chips.txt")
        .replace("{agent_name}", agent.name)
        .replace("{agent_summary}", (agent.function_summary or "")[:500])
        .replace("{input_name}", input_name)
        .replace("{input_label}", human_input_label(input_name))
        .replace("{problem_statement}", query[:1500])
        .replace("{history}", _format_history(messages))
        .replace("{prior_answers}", _format_prior_answers(spec))
        .replace("{question}", question[:500])
        .replace(
            "{existing_chips}",
            "\n".join(f"- {c}" for c in existing[:6]) if existing else "(none)",
        )
    )
    try:
        raw = call_llm(
            client,
            settings,
            system,
            "Return the JSON object with chips for this agent input.",
            json_mode=True,
            temperature=0.2,
        )
        parsed = json.loads(strip_json_fences(raw))
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("LLM chip generation parse failed: %s", exc)
        return None

    raw_chips = parsed.get("chips") if isinstance(parsed, dict) else None
    if not isinstance(raw_chips, list):
        return None

    chips: list[str] = []
    for item in raw_chips:
        text = _normalize_chip(str(item).strip())
        if text and not is_other_chip(text):
            chips.append(text)

    gated = gate_chip_list(
        chips,
        input_name=input_name,
        agent_summary=agent.function_summary or "",
    )
    if len(gated) < 2:
        return None

    idx = parsed.get("suggested_index", 0)
    try:
        suggested_index = int(idx)
    except (TypeError, ValueError):
        suggested_index = 0
    if suggested_index < 0 or suggested_index >= len(gated):
        suggested_index = 0

    grounding = parsed.get("grounding")
    ground_list = (
        [str(g).strip() for g in grounding if str(g).strip()]
        if isinstance(grounding, list)
        else None
    )

    return LlmChipGeneration(
        chips=gated,
        suggested_index=suggested_index,
        grounding=ground_list,
    )


def build_agent_input_chips(
    agent: AgentRecord,
    input_name: str,
    query: str,
    settings: Settings,
    *,
    deterministic: list[str],
    spec: ArchitectureSpec | None = None,
    messages: list[ChatMessage] | None = None,
    llm_chips: list[str] | None = None,
    turn_index: int = 0,
    client: AzureOpenAI | None = None,
    question_text: str = "",
) -> tuple[list[str], str | None, str]:
    """
    Tiered chip build for one agent input.
    Returns (chips, suggested_chip, suggestion_reason).
    """
    catalog = _load_catalog(settings)
    catalog_patterns = catalog_values_for_input(catalog, agent, input_name)

    ranked_catalog = _rank_chips(
        query,
        catalog_patterns,
        field_key=input_name,
        turn_index=turn_index,
    )

    contextual: list[str] = []
    if spec is not None and messages is not None:
        contextual = contextual_chips_from_conversation(
            f"agent_input:{input_name}",
            spec,
            messages,
        )

    agent_summary = agent.function_summary or ""
    tier12_count = _tier12_gated_count(
        deterministic=deterministic,
        catalog=ranked_catalog,
        contextual=contextual,
        input_name=input_name,
        agent_summary=agent_summary,
    )

    llm_tier: list[str] = []
    llm_suggested_index: int | None = None
    llm_grounding: list[str] | None = None
    used_p3_llm = False

    interview_llm = [
        c.strip()
        for c in (llm_chips or [])
        if c.strip() and not is_other_chip(c)
    ]

    if (
        not interview_uses_fast_chips()
        and tier12_count < MIN_TIER_CHIPS_BEFORE_LLM
        and client is not None
    ):
        gen = generate_llm_chips_for_input(
            agent,
            input_name,
            question_text or f"How should we configure {human_input_label(input_name)}?",
            query,
            settings,
            client,
            spec=spec,
            messages=messages,
            existing_chips=deterministic + ranked_catalog + contextual,
        )
        if gen:
            llm_tier = gen.chips
            llm_suggested_index = gen.suggested_index
            llm_grounding = gen.grounding
            used_p3_llm = True

    merged = merge_and_gate_chips(
        deterministic=deterministic,
        catalog=ranked_catalog,
        contextual=contextual,
        llm=interview_llm + llm_tier,
        input_name=input_name,
        agent_summary=agent_summary,
    )

    if llm_suggested_index is not None and llm_tier:
        core = [c for c in merged if not is_other_chip(c)]
        if 0 <= llm_suggested_index < len(llm_tier):
            pick = llm_tier[llm_suggested_index]
            if pick in core:
                suggested = pick
            else:
                suggested = pick_suggested_chip(merged, query=query)
        else:
            suggested = pick_suggested_chip(merged, query=query)
    else:
        suggested = pick_suggested_chip(merged, query=query)

    if deterministic:
        first_det = next((c for c in deterministic if c != OTHER_CHIP), None)
        if first_det and first_det in merged and not used_p3_llm:
            suggested = first_det

    reason_parts = [f"Grounded in catalog input `{input_name}` for {agent.name}"]
    if ranked_catalog:
        reason_parts.append("similar delivery patterns from spec.json")
    if spec and spec.transcript_summary:
        reason_parts.append("your earlier answers")
    if used_p3_llm:
        reason_parts.append("AI-generated options for this input")
        if llm_grounding:
            reason_parts.append(llm_grounding[0][:120])

    return merged, suggested, " · ".join(reason_parts) + "."


def human_input_label(input_name: str) -> str:
    """Plain label for questions (not raw field ids)."""
    text = (input_name or "").replace("_", " ").strip()
    if not text:
        return "this setting"
    return text[0].upper() + text[1:]
