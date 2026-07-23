"""Minimal BaseAgent contract for workflow nodes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IOFieldType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    FILE = "file"
    UNKNOWN = "unknown"


@dataclass
class AgentMetadata:
    agent_id: str
    label: str
    description: str = ""
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)


class BaseAgent(ABC):
    """Workflow node base class with input/output validation hooks."""

    metadata: AgentMetadata

    def validate_input(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload

    @abstractmethod
    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Perform the node's primary operation."""

    def validate_output(self, result: dict[str, Any]) -> dict[str, Any]:
        return result

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        validated = self.validate_input(payload)
        result = self.execute(validated)
        return self.validate_output(result)


class LLMAgent(BaseAgent):
    """LLM-backed agent — subclasses implement prompt and parsing logic."""

    requires_llm: bool = True
