"""Minimal BaseAgent / LLMAgent stubs for build and reuse agent compatibility."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IOFieldType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    UNKNOWN = "unknown"


@dataclass
class AgentMetadata:
    agent_id: str
    name: str
    description: str = ""
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)


class BaseAgent(ABC):
    """Abstract base for workflow agents."""

    metadata: AgentMetadata

    def validate_input(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload

    @abstractmethod
    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    def validate_output(self, result: dict[str, Any]) -> dict[str, Any]:
        return result


class LLMAgent(BaseAgent):
    """Base for LLM-backed agents with optional client injection."""

    def __init__(self, llm_client: Any | None = None) -> None:
        self.llm_client = llm_client
