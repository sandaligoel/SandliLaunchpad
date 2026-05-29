"""Agent-centric setup interview (spec.json inputs) for Agent Launchpad."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class MatchedAgentSummary(BaseModel):
    agent_id: str
    name: str
    reason: str


class AgentSetupQuestionItem(BaseModel):
    field_key: str
    agent_id: str
    agent_name: str
    input_name: str
    question: str
    chips: list[str] = Field(default_factory=list)
    cluster: str = "General Configuration"
    impact_score: int = 50
    dependency_score: int = 50
    uncertainty_score: int = 50
    business_criticality_score: int = 50
    rank_score: float = 50.0


WorkflowPhase = Literal["start", "interview", "completion_check", "handover"]


class AgentWorkflowState(BaseModel):
    query_understood: str = ""
    matched_agents: list[MatchedAgentSummary] = Field(default_factory=list)
    questions: list[AgentSetupQuestionItem] = Field(default_factory=list)
    answers: dict[str, str] = Field(default_factory=dict)
    next_index: int = 0  # legacy counter; completion uses unanswered queue
    current_phase: WorkflowPhase = "start"
    question_count: int = 0
    question_budget: int = 18
    hard_cap: int = 25
    coverage_score: float = 0.0
    risk_score: float = 10.0
    required_input_count: int = 0
    critical_items: list[str] = Field(default_factory=list)
    completion_reason: str | None = None
    current_cluster: str | None = None

    def is_complete(self) -> bool:
        """True when no pending questions remain (see agent_workflow_interview)."""
        answered = {k for k, v in self.answers.items() if str(v).strip()}
        for q in self.questions:
            if q.field_key not in answered:
                return False
        return True
