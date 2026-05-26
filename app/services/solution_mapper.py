"""Map parsed solution catalog entries to ProjectKnowledge."""

from __future__ import annotations

from app.schemas.extraction import (
    AgentKnowledge,
    ArchitectureKnowledge,
    ExtractionMetadata,
    IntegrationKnowledge,
    OrchestrationKnowledge,
    OrchestrationPattern,
    ProjectKnowledge,
    SourceDocument,
    WorkflowKnowledge,
)
from app.schemas.solution_document import ParsedSolution, ParsedSolutionAgent
from app.utils.text import dedupe_preserve_order


def _retrieval_used(agent: ParsedSolutionAgent) -> bool:
    text = f"{agent.agent_name} {agent.model_used} {agent.function_summary}".lower()
    return any(k in text for k in ("graphrag", "rag", "lancedb", "vector", "embedding", "search index"))


def solution_to_project_knowledge(
    solution: ParsedSolution,
    project_id: str,
    source_filename: str,
    content_hash: str,
) -> ProjectKnowledge:
    agents = [
        AgentKnowledge(
            agent_id=f"{project_id}:agent:{i}",
            agent_name=a.agent_name,
            purpose=a.function_summary,
            inputs=a.inputs,
            outputs=a.outputs,
            llm_used=a.model_used,
            tools_used=[],
            external_integrations=[],
            workflow_position=a.workflow_position,
            retrieval_used=_retrieval_used(a),
            decision_logic="",
            confidence_score=1.0,
        )
        for i, a in enumerate(solution.agents)
    ]

    models = dedupe_preserve_order(
        [a.model_used for a in solution.agents if a.model_used]
    )
    vector_dbs = [t for t in solution.tech_stack if "lance" in t.lower() or "vector" in t.lower()]

    integrations = [
        IntegrationKnowledge(name=name, integration_type="external", purpose=name)
        for name in solution.integrations
    ]

    cloud = "Azure" if any("azure" in t.lower() for t in solution.tech_stack) else ""

    arch = ArchitectureKnowledge(
        pattern="Multi-agent solution pipeline",
        communication_style="REST API / FastAPI orchestration",
        orchestration_framework="FastAPI",
        deployment="Enterprise web application",
        cloud_provider=cloud,
        scalability_notes=solution.solution_summary[:500],
        confidence_score=1.0,
    )

    orch = OrchestrationKnowledge(
        framework="FastAPI",
        pattern=OrchestrationPattern.SEQUENTIAL
        if solution.workflow_steps
        else OrchestrationPattern.UNKNOWN,
        agent_graph_description=" → ".join(a.agent_name for a in solution.agents[:12]),
        confidence_score=1.0,
    )

    workflow = WorkflowKnowledge(
        workflow_id=f"{project_id}:workflow:main",
        name=f"{solution.project_name} — Data Flow",
        description=solution.solution_summary,
        steps=solution.workflow_steps or [a.agent_name for a in solution.agents],
        confidence_score=1.0,
    )

    outcomes = (
        [solution.outcomes]
        if solution.outcomes and ";" not in solution.outcomes[:80]
        else [o.strip() for o in solution.outcomes.split(";") if o.strip()]
    )

    return ProjectKnowledge(
        project_id=project_id,
        project_name=solution.project_name,
        industry=solution.vertical,
        business_problem=solution.business_problem,
        summary=solution.solution_summary,
        agents=agents,
        workflows=[workflow],
        architecture=arch,
        orchestration=orch,
        tech_stack=solution.tech_stack,
        models_used=models,
        vector_databases=vector_dbs,
        apis_used=[],
        integrations=integrations,
        workflow_description="\n".join(solution.workflow_steps[:20]),
        business_outcomes=outcomes,
        source_document=SourceDocument(
            filename=source_filename,
            content_hash=content_hash,
        ),
        extraction_metadata=ExtractionMetadata(
            confidence_score=1.0,
            model_version="solution-catalog-parser",
            extraction_notes=f"Parsed from solution catalog PDF; client={solution.client}",
        ),
    )
