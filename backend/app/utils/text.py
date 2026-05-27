"""Text normalization and embedding text builders."""

import re
from typing import Iterable

from backend.app.schemas.extraction import (
    AgentKnowledge,
    ArchitectureKnowledge,
    OrchestrationKnowledge,
    ProjectKnowledge,
    WorkflowKnowledge,
)


def normalize_whitespace(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def dedupe_preserve_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(item.strip())
    return result


def merge_agent_lists(agents: list[AgentKnowledge]) -> list[AgentKnowledge]:
    by_name: dict[str, AgentKnowledge] = {}
    for agent in agents:
        key = agent.agent_name.strip().lower() or f"unnamed-{id(agent)}"
        if key in by_name:
            existing = by_name[key]
            merged_tools = dedupe_preserve_order(
                [*existing.tools_used, *agent.tools_used]
            )
            merged_caps = dedupe_preserve_order(
                [*existing.capabilities, *agent.capabilities]
            )
            by_name[key] = existing.model_copy(
                update={
                    "purpose": agent.purpose or existing.purpose,
                    "tools_used": merged_tools,
                    "capabilities": merged_caps,
                    "confidence_score": max(
                        existing.confidence_score, agent.confidence_score
                    ),
                }
            )
        else:
            by_name[key] = agent
    return list(by_name.values())


def build_project_embed_text(project: ProjectKnowledge) -> str:
    parts = [
        f"Project: {project.project_name}",
        f"Industry: {project.industry}" if project.industry else "",
        f"Problem: {project.business_problem}" if project.business_problem else "",
        project.summary,
        f"Outcomes: {', '.join(project.business_outcomes)}" if project.business_outcomes else "",
        f"Tech: {', '.join(project.tech_stack)}" if project.tech_stack else "",
    ]
    return normalize_whitespace(". ".join(p for p in parts if p))


def build_agent_embed_text(agent: AgentKnowledge, project_name: str = "") -> str:
    parts = [
        f"Project: {project_name}" if project_name else "",
        f"Agent: {agent.agent_name}",
        f"Purpose: {agent.purpose}",
        f"Inputs: {', '.join(agent.inputs)}" if agent.inputs else "",
        f"Outputs: {', '.join(agent.outputs)}" if agent.outputs else "",
        f"LLM: {agent.llm_used}" if agent.llm_used else "",
        f"Tools: {', '.join(agent.tools_used)}" if agent.tools_used else "",
        f"Decision logic: {agent.decision_logic}" if agent.decision_logic else "",
        f"Integrations: {', '.join(agent.external_integrations)}"
        if agent.external_integrations
        else "",
        f"Capabilities: {', '.join(agent.capabilities)}" if agent.capabilities else "",
        f"Position: {agent.workflow_position}" if agent.workflow_position else "",
    ]
    return normalize_whitespace(". ".join(p for p in parts if p))


def build_workflow_embed_text(workflow: WorkflowKnowledge, project_name: str = "") -> str:
    parts = [
        f"Project: {project_name}" if project_name else "",
        f"Workflow: {workflow.name}",
        workflow.description,
        f"Steps: {'; '.join(workflow.steps)}" if workflow.steps else "",
        workflow.orchestration_notes,
    ]
    return normalize_whitespace(". ".join(p for p in parts if p))


def build_architecture_embed_text(
    arch: ArchitectureKnowledge,
    orch: OrchestrationKnowledge | None = None,
    project_name: str = "",
) -> str:
    parts = [
        f"Project: {project_name}" if project_name else "",
        f"Pattern: {arch.pattern}",
        f"Communication: {arch.communication_style}",
        f"Deployment: {arch.deployment}",
        f"Cloud: {arch.cloud_provider}",
        f"Framework: {arch.orchestration_framework}",
        arch.scalability_notes,
        arch.security_notes,
        arch.latency_constraints,
    ]
    if orch:
        parts.extend([
            f"Orchestration pattern: {orch.pattern.value}",
            orch.agent_graph_description,
        ])
    return normalize_whitespace(". ".join(p for p in parts if p))


def truncate_for_embedding(text: str, max_chars: int = 8000) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."
