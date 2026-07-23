"""Base agent classes for build-node implementations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentMetadata:
    agent_id: str
    label: str
    version: str = "1.0.0"
    description: str = ""


class BaseAgent:
    """Minimal agent base class used by build nodes."""

    metadata: AgentMetadata

    def validate_input(self, data: dict[str, Any]) -> dict[str, Any]:
        return dict(data)

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError(f"{self.metadata.agent_id} must implement execute()")

    def validate_output(self, data: dict[str, Any]) -> dict[str, Any]:
        return dict(data)

    def run(self, data: dict[str, Any]) -> dict[str, Any]:
        validated = self.validate_input(data)
        result = self.execute(validated)
        return self.validate_output(result)


class LLMAgent(BaseAgent):
    """Optional LLM-enabled base class for future extensions."""

    llm_client: Any | None = None

    def __init__(self, llm_client: Any | None = None) -> None:
        self.llm_client = llm_client
