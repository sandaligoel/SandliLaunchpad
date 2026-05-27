"""Semantic chunks tailored for solution catalog PDF segments."""

from __future__ import annotations

from backend.app.schemas.chunking import SemanticChunk
from backend.app.schemas.extraction import SectionType
from backend.app.schemas.solution_document import ParsedSolution, SolutionCatalogDocument
from backend.app.utils.ids import generate_chunk_id, generate_section_id
from backend.app.utils.text import normalize_whitespace


class SolutionCatalogChunker:
    """Builds agent-centric and section-centric chunks from parsed catalog solutions."""

    def chunk_catalog(
        self,
        catalog: SolutionCatalogDocument,
        document_id: str,
    ) -> dict[str, list[SemanticChunk]]:
        """Returns project_name -> chunks for indexing."""
        per_project: dict[str, list[SemanticChunk]] = {}
        for solution in catalog.solutions:
            per_project[solution.project_name] = self._chunk_solution(
                solution, document_id
            )
        return per_project

    def _chunk_solution(
        self, solution: ParsedSolution, document_id: str
    ) -> list[SemanticChunk]:
        chunks: list[SemanticChunk] = []
        proj_slug = solution.project_name[:40]

        overview = normalize_whitespace(
            f"Project: {solution.project_name}\n"
            f"Client: {solution.client}\n"
            f"Vertical: {solution.vertical}\n"
            f"Problem: {solution.business_problem}\n"
            f"Summary: {solution.solution_summary}"
        )
        if overview.strip():
            chunks.append(
                self._chunk(
                    document_id,
                    f"{proj_slug}-overview",
                    SectionType.PROJECT_OVERVIEW,
                    "Project Overview",
                    overview,
                    metadata={"project_name": solution.project_name},
                )
            )

        if solution.workflow_steps:
            flow_text = "\n".join(
                f"{i + 1}. {s}" for i, s in enumerate(solution.workflow_steps)
            )
            chunks.append(
                self._chunk(
                    document_id,
                    f"{proj_slug}-workflow",
                    SectionType.WORKFLOW,
                    "Data Flow",
                    flow_text,
                    metadata={"project_name": solution.project_name},
                )
            )

        if solution.tech_stack:
            chunks.append(
                self._chunk(
                    document_id,
                    f"{proj_slug}-tech",
                    SectionType.TECH_STACK,
                    "Tech Stack",
                    ", ".join(solution.tech_stack),
                    metadata={"project_name": solution.project_name},
                )
            )

        for i, agent in enumerate(solution.agents):
            content = normalize_whitespace(
                f"Agent: {agent.agent_name}\n"
                f"Function: {agent.function_summary}\n"
                f"Input: {'; '.join(agent.inputs)}\n"
                f"Output: {'; '.join(agent.outputs)}\n"
                f"Model: {agent.model_used}\n"
                f"Position: {agent.workflow_position}\n"
                f"{agent.raw_content[:1500]}"
            )
            chunks.append(
                self._chunk(
                    document_id,
                    f"{proj_slug}-agent-{i}",
                    SectionType.AGENT,
                    agent.agent_name,
                    content,
                    metadata={
                        "project_name": solution.project_name,
                        "agent_name": agent.agent_name,
                    },
                )
            )

        return chunks

    @staticmethod
    def _chunk(
        document_id: str,
        section_key: str,
        section_type: SectionType,
        title: str,
        content: str,
        metadata: dict[str, str],
    ) -> SemanticChunk:
        section_id = generate_section_id(document_id, section_key, 1)
        return SemanticChunk(
            chunk_id=generate_chunk_id(document_id, section_id, 0),
            document_id=document_id,
            section_id=section_id,
            section_type=section_type,
            section_title=title,
            content=content,
            page_start=1,
            page_end=1,
            hierarchy_level=1 if section_type == SectionType.AGENT else 0,
            metadata=metadata,
            token_estimate=len(content) // 4,
        )
