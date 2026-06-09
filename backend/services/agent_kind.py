"""Classify catalog entries as agent, function, or tool for UI labeling."""

from __future__ import annotations

from typing import Literal

from schemas.agent_record import AgentRecord

ImplementationKind = Literal["agent", "function", "tool"]


def classify_implementation_kind(agent: AgentRecord) -> ImplementationKind:
    """
    Infer how a catalog step is implemented:

    - agent: multi-agent chains or LLM-orchestrated modules
    - function: single LLM callable (llm_functions.py style)
    - tool: deterministic services, CV models, indexes, API wrappers
    """
    notes = (agent.notes or "").lower()
    tech_blob = " ".join(agent.tech_stack).lower()
    name = agent.name.lower()
    summary = agent.function_summary.lower()
    blob = f"{notes} {tech_blob} {name} {summary}"

    if "agents:" in notes or "agent chain" in name or "autogen" in tech_blob:
        return "agent"

    if "llm_functions" in tech_blob or "llm_functions" in notes:
        return "function"
    if any(
        token in notes
        for token in (
            "count_function",
            "generic_function",
            "final_answer_function",
            "daily_kpi",
        )
    ):
        return "function"

    if " agent" in name or name.endswith(" agent") or " chain" in name:
        if "llm_functions" not in tech_blob:
            return "agent"

    tool_markers = (
        "roboflow",
        "detect_crop.py",
        "yolo",
        "catboost",
        "scikit-learn",
        "sklearn",
        "images/edits",
        "videos api",
        "azure-search-documents",
        "semantic.py",
        "competitive_scoring.py",
        "not a trained ml model",
        "sql_tool",
    )
    if any(marker in blob for marker in tool_markers):
        return "tool"

    if "python-docx" in tech_blob and "azure openai" not in tech_blob:
        return "tool"

    if any(
        phrase in name
        for phrase in (
            "embedder",
            "vector retrieval",
            "semantic search",
            "row detector",
            "product detector",
            "simulator",
            "stub",
            "analysis engine",
        )
    ):
        return "tool"

    if "deterministic" in blob and "azure openai" not in tech_blob:
        return "tool"

    if "azure openai" in tech_blob or "graphrag" in tech_blob or "google-genai" in tech_blob:
        return "agent"

    if "python" in tech_blob and "openai" not in tech_blob and "genai" not in tech_blob:
        return "tool"

    return "agent"
