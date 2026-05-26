"""Transforms ProjectKnowledge + chunks into search documents and indexes them."""

from __future__ import annotations

import json
from datetime import datetime

from app.embeddings.azure_embeddings import AzureEmbeddingService
from app.schemas.chunking import SemanticChunk
from app.schemas.extraction import ProjectKnowledge
from app.schemas.search import EntityType, SearchDocument
from app.search.index_manager import IndexManager
from app.utils.ids import generate_entity_index_id
from app.utils.text import (
    build_agent_embed_text,
    build_architecture_embed_text,
    build_project_embed_text,
    build_workflow_embed_text,
    truncate_for_embedding,
)


class IndexingService:
    """Builds search documents from extracted knowledge and upserts to Azure AI Search."""

    def __init__(
        self,
        index_manager: IndexManager | None = None,
        embedding_service: AzureEmbeddingService | None = None,
    ) -> None:
        self.index_manager = index_manager or IndexManager()
        self.embeddings = embedding_service or AzureEmbeddingService()

    async def build_and_index(
        self,
        project: ProjectKnowledge,
        chunks: list[SemanticChunk],
        filename: str,
    ) -> tuple[int, dict[str, int]]:
        documents = self._build_documents(project, chunks, filename)
        texts = [d.content for d in documents]
        vectors = await self.embeddings.embed_batch(texts)
        for doc, vector in zip(documents, vectors, strict=True):
            doc.content_vector = vector

        count = self.index_manager.upsert_documents(documents)
        breakdown: dict[str, int] = {}
        for doc in documents:
            et = doc.entity_type.value
            breakdown[et] = breakdown.get(et, 0) + 1
        return count, breakdown

    def _build_documents(
        self,
        project: ProjectKnowledge,
        chunks: list[SemanticChunk],
        filename: str,
    ) -> list[SearchDocument]:
        docs: list[SearchDocument] = []
        ingested = datetime.utcnow()
        source = project.source_document

        project_content = build_project_embed_text(project)
        docs.append(
            SearchDocument(
                id=generate_entity_index_id(project.project_id, "project", project.project_name),
                entity_type=EntityType.PROJECT,
                project_id=project.project_id,
                project_name=project.project_name,
                industry=project.industry,
                title=project.project_name or "Untitled Project",
                content=project_content,
                tech_stack=project.tech_stack,
                models_used=project.models_used,
                source_filename=filename,
                confidence_score=project.extraction_metadata.confidence_score,
                ingested_at=ingested,
                structured_payload=project.model_dump_json(),
            )
        )

        for agent in project.agents:
            content = build_agent_embed_text(agent, project.project_name)
            docs.append(
                SearchDocument(
                    id=generate_entity_index_id(
                        project.project_id, "agent", agent.agent_name or agent.agent_id
                    ),
                    entity_type=EntityType.AGENT,
                    project_id=project.project_id,
                    project_name=project.project_name,
                    industry=project.industry,
                    title=agent.agent_name or "Unnamed Agent",
                    content=content,
                    agent_name=agent.agent_name,
                    agent_purpose=agent.purpose,
                    tech_stack=project.tech_stack,
                    models_used=[agent.llm_used] if agent.llm_used else project.models_used,
                    tools_used=agent.tools_used,
                    capabilities=agent.capabilities,
                    retrieval_used=agent.retrieval_used,
                    source_filename=filename,
                    confidence_score=agent.confidence_score,
                    ingested_at=ingested,
                    structured_payload=agent.model_dump_json(),
                )
            )

        for workflow in project.workflows:
            content = build_workflow_embed_text(workflow, project.project_name)
            docs.append(
                SearchDocument(
                    id=generate_entity_index_id(
                        project.project_id, "workflow", workflow.name or workflow.workflow_id
                    ),
                    entity_type=EntityType.WORKFLOW,
                    project_id=project.project_id,
                    project_name=project.project_name,
                    industry=project.industry,
                    title=workflow.name or "Workflow",
                    content=content,
                    workflow_keywords=workflow.steps[:20],
                    orchestration_framework=project.orchestration.framework,
                    source_filename=filename,
                    confidence_score=workflow.confidence_score,
                    ingested_at=ingested,
                    structured_payload=workflow.model_dump_json(),
                )
            )

        arch = project.architecture
        arch_content = build_architecture_embed_text(
            arch, project.orchestration, project.project_name
        )
        docs.append(
            SearchDocument(
                id=generate_entity_index_id(
                    project.project_id, "architecture", project.project_name
                ),
                entity_type=EntityType.ARCHITECTURE,
                project_id=project.project_id,
                project_name=project.project_name,
                industry=project.industry,
                title=f"Architecture — {project.project_name}",
                content=arch_content,
                architecture_pattern=arch.pattern,
                orchestration_framework=arch.orchestration_framework
                or project.orchestration.framework,
                cloud_provider=arch.cloud_provider,
                deployment_model=arch.deployment_model or arch.deployment,
                tech_stack=project.tech_stack,
                models_used=project.models_used,
                source_filename=filename,
                confidence_score=arch.confidence_score,
                ingested_at=ingested,
                structured_payload=json.dumps({
                    "architecture": arch.model_dump(),
                    "orchestration": project.orchestration.model_dump(),
                }),
            )
        )

        for chunk in chunks:
            chunk_title = f"{chunk.section_type.value}: {chunk.section_title}"
            content = truncate_for_embedding(
                f"{chunk_title}. {chunk.content}"
            )
            docs.append(
                SearchDocument(
                    id=generate_entity_index_id(
                        project.project_id, "chunk", chunk.chunk_id
                    ),
                    entity_type=EntityType.CHUNK,
                    project_id=project.project_id,
                    project_name=project.project_name,
                    industry=project.industry,
                    title=chunk_title,
                    content=content,
                    source_filename=filename,
                    source_page_start=chunk.page_start,
                    source_page_end=chunk.page_end,
                    ingested_at=ingested,
                    structured_payload=json.dumps({
                        "chunk_id": chunk.chunk_id,
                        "section_type": chunk.section_type.value,
                    }),
                )
            )

        if source:
            for doc in docs:
                if not doc.source_filename:
                    doc.source_filename = source.filename
        return docs
