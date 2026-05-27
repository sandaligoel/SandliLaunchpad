"""Models for LLM extraction pipeline output."""

from __future__ import annotations  # noqa: F401 — enables PEP 604 unions on 3.9+

from typing import Optional

from pydantic import BaseModel, Field

from schemas.agent_record import AgentRecord, ProjectRecord


class ExtractionOutput(BaseModel):
    """Result of extracting project and agent records from a single chunk."""

    project: Optional[ProjectRecord] = None
    agents: list[AgentRecord] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
