"""Maps ProjectSpecDocument JSON to ProjectKnowledge for indexing."""

from __future__ import annotations

from app.schemas.extraction import (
    AgentKnowledge,
    ArchitectureKnowledge,
    EntityRelationship,
    ExtractionMetadata,
    IntegrationKnowledge,
    OrchestrationKnowledge,
    OrchestrationPattern,
    ProjectKnowledge,
    RelationType,
    SourceDocument,
    WorkflowKnowledge,
)
from app.schemas.spec_import import ProjectSpecDocument, SpecAgent
from app.utils.ids import content_hash, slugify
from app.utils.text import dedupe_preserve_order


def _uses_retrieval(agent: SpecAgent) -> bool:
    text = f"{agent.name} {agent.function_summary} {' '.join(agent.tech_stack)}".lower()
    return any(k in text for k in ("graphrag", "lancedb", "embedding", "retrieval", "rag"))


def _collect_models(agents: list[SpecAgent]) -> list[str]:
    models: list[str] = []
    for a in agents:
        if a.model_used:
            models.append(a.model_used.split("(")[0].strip())
    return dedupe_preserve_order(models)


def spec_to_project_knowledge(
    spec: ProjectSpecDocument,
    project_id: str,
    source_filename: str = "spec.json",
) -> ProjectKnowledge:
    p = spec.project
    agents: list[AgentKnowledge] = []

    for i, a in enumerate(spec.agents):
        agents.append(
            AgentKnowledge(
                agent_id=f"{project_id}:agent:{slugify(a.name)}",
                agent_name=a.name,
                purpose=a.function_summary,
                inputs=a.inputs,
                outputs=a.outputs,
                llm_used=a.model_used,
                tools_used=a.tech_stack,
                external_integrations=a.integrations,
                capabilities=[a.category] if a.category else [],
                workflow_position=f"{i + 1}/{len(spec.agents)} — {a.category}",
                retrieval_used=_uses_retrieval(a),
                decision_logic=a.notes,
                confidence_score=1.0,
            )
        )

    vector_dbs = [t for t in p.tech_stack if "lance" in t.lower() or "vector" in t.lower()]
    if not vector_dbs and any("GraphRAG" in t or "LanceDB" in t for t in p.tech_stack):
        vector_dbs = [t for t in p.tech_stack if "LanceDB" in t or "GraphRAG" in t]

    integrations = [
        IntegrationKnowledge(name=i, integration_type="external", purpose=i)
        for i in dedupe_preserve_order(
            [x for a in spec.agents for x in a.integrations]
        )
    ]

    relationships: list[EntityRelationship] = []
    for agent in spec.agents:
        for integration in agent.integrations:
            relationships.append(
                EntityRelationship(
                    source_type="agent",
                    source_name=agent.name,
                    target_type="integration",
                    target_name=integration,
                    relation=RelationType.USES,
                )
            )

    arch = ArchitectureKnowledge(
        pattern="Multi-agent KYC pre-screening pipeline with GraphRAG Q&A",
        communication_style="REST API orchestration via FastAPI; sequential agent pipeline",
        orchestration_framework="FastAPI agent pipeline (pipeline_full.py)",
        deployment="Web application — React frontend + FastAPI backend on Azure",
        cloud_provider="Azure",
        deployment_model="Azure Blob Storage + Azure SQL Server + Azure OpenAI",
        scalability_notes="Per-project GraphRAG indexing in background threads",
        security_notes="KYC policy-gated ingestion; human-in-the-loop for client emails",
        confidence_score=1.0,
    )

    orchestration = OrchestrationKnowledge(
        framework="FastAPI",
        pattern=OrchestrationPattern.SEQUENTIAL,
        agent_graph_description=(
            "Upload → Entity Extraction → Policy Validator → "
            "(block | Risk Scoring → Reasoning → UBO Analysis) → Report; "
            "parallel GraphRAG indexing; optional email drafter on policy block"
        ),
        confidence_score=1.0,
    )

    workflow = WorkflowKnowledge(
        workflow_id=f"{project_id}:workflow:main",
        name="KYC Pre-Screening Pipeline",
        description=p.solution_summary,
        steps=[a.name for a in spec.agents],
        triggers=["Document upload (PDF/TXT/DOCX)", "Analyst risk assessment request"],
        orchestration_notes=orchestration.agent_graph_description,
        confidence_score=1.0,
    )

    outcomes_list = (
        [p.outcomes] if p.outcomes and "\n" not in p.outcomes[:50] else p.outcomes.split(";")
    )
    outcomes_list = [o.strip() for o in outcomes_list if o.strip()]

    return ProjectKnowledge(
        project_id=project_id,
        project_name=p.name,
        industry=p.vertical,
        business_problem=p.business_problem,
        summary=p.solution_summary,
        agents=agents,
        workflows=[workflow],
        architecture=arch,
        orchestration=orchestration,
        tech_stack=p.tech_stack,
        models_used=_collect_models(spec.agents),
        vector_databases=vector_dbs or ["LanceDB"],
        apis_used=["Microsoft Graph API", "FastAPI REST"],
        integrations=integrations,
        workflow_description=p.solution_summary,
        business_outcomes=outcomes_list,
        relationships=relationships,
        source_document=SourceDocument(
            filename=source_filename,
            content_hash=content_hash(spec.model_dump_json()),
        ),
        extraction_metadata=ExtractionMetadata(
            confidence_score=1.0,
            model_version="spec-import",
            extraction_notes=f"Imported from structured spec; client={p.client}",
        ),
    )
