"""Pydantic models for agent and project catalog records."""

from __future__ import annotations

import re
from typing import Literal, Optional, get_args

from pydantic import BaseModel, Field

Category = Literal[
    "Finance & Procurement",
    "Document & Data",
    "Quality & Compliance",
    "Supply Chain & Logistics",
    "Sales & Revenue",
    "Healthcare & Compliance",
]

Vertical = Literal[
    "CPG",
    "Retail",
    "Healthcare",
    "Manufacturing",
    "Finance",
    "Other",
]

_VERTICAL_VALUES: frozenset[str] = frozenset(get_args(Vertical))

_VERTICAL_ALIASES: dict[str, Vertical] = {
    "financial": "Finance",
    "financial services": "Finance",
    "banking": "Finance",
    "consumer packaged goods": "CPG",
    "fmcg": "CPG",
    "retail / cpg": "Retail",
    "retail/cpg": "Retail",
    "retail and cpg": "Retail",
    "cpg / retail": "Retail",
    "health care": "Healthcare",
    "life sciences": "Healthcare",
    "industrial": "Manufacturing",
}


def normalize_vertical(value: str | None) -> Vertical:
    """
    Map LLM or PDF text to a canonical vertical, defaulting to Other.

    Accepts known literals case-insensitively and common synonyms (e.g. Banking → Finance).
    """
    if not value or not str(value).strip():
        return "Other"
    text = str(value).strip()
    if text in _VERTICAL_VALUES:
        return text  # type: ignore[return-value]
    lowered = text.lower()
    mapped = _VERTICAL_ALIASES.get(lowered)
    if mapped:
        return mapped
    if "retail" in lowered and "cpg" in lowered:
        return "Retail"
    if "finance" in lowered or "banking" in lowered:
        return "Finance"
    for canonical in _VERTICAL_VALUES:
        if text.lower() == canonical.lower():
            return canonical  # type: ignore[return-value]
    return "Other"

AgentStatus = Literal["live", "available", "deprecated"]
ImplementationKind = Literal["agent", "function", "tool"]


def slugify(text: str) -> str:
    """
    Convert text to a URL-safe slug for use as record IDs.

    Lowercases, strips special characters, and replaces spaces with hyphens.
    """
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


class AgentRecord(BaseModel):
    """Structured record for a single AI agent extracted from the solutions PDF."""

    id: str = ""
    name: str
    version: str = "1.0"
    category: Category
    function_summary: str
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    model_used: str = "Unknown"
    tech_stack: list[str] = Field(default_factory=list)
    integrations: list[str] = Field(default_factory=list)
    origin_project: str = ""
    origin_client: str = ""
    vertical: Vertical = "Other"
    status: AgentStatus = "available"
    typical_accuracy: Optional[str] = None
    notes: Optional[str] = None
    source_page: int
    embedding: Optional[list[float]] = None
    implementation_kind: ImplementationKind = "agent"


class ProjectRecord(BaseModel):
    """Structured record for a client project extracted from the solutions PDF."""

    id: str = ""
    name: str
    client: str = ""
    vertical: Vertical = "Other"
    business_problem: str = ""
    solution_summary: str = ""
    agents_used: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    outcomes: Optional[str] = None
    source_page: int
