"""Azure OpenAI structured extraction with validation and merge."""

from __future__ import annotations

import asyncio
import json
from typing import TypeVar

from openai import AsyncAzureOpenAI
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.core.exceptions import ConfigurationError, ExtractionError
from app.core.logging import get_logger
from app.core.retry import llm_retry
from app.prompts.extraction import (
    CHUNK_EXTRACTION_SYSTEM,
    CHUNK_EXTRACTION_USER,
    MERGE_EXTRACTION_SYSTEM,
    MERGE_EXTRACTION_USER,
)
from app.schemas.chunking import SemanticChunk
from app.schemas.extraction import ChunkExtraction, ProjectKnowledge
from app.utils.text import dedupe_preserve_order, merge_agent_lists

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMExtractor:
    """Two-pass extraction: chunk-level grounding + document merge."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.azure_openai_endpoint or not settings.azure_openai_api_key:
            raise ConfigurationError(
                "Azure OpenAI endpoint and API key are required",
                {"vars": ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"]},
            )
        self.settings = settings
        self.client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
        self.deployment = settings.azure_openai_chat_deployment
        self.temperature = settings.extraction_temperature

    async def extract_chunks(
        self, chunks: list[SemanticChunk], max_concurrency: int = 5
    ) -> list[ChunkExtraction]:
        semaphore = asyncio.Semaphore(max_concurrency)
        results: list[ChunkExtraction | None] = [None] * len(chunks)

        async def process(idx: int, chunk: SemanticChunk) -> None:
            async with semaphore:
                try:
                    results[idx] = await self._extract_chunk(chunk)
                except Exception as e:
                    logger.error(
                        "chunk_extraction_failed",
                        chunk_id=chunk.chunk_id,
                        error=str(e),
                    )
                    results[idx] = ChunkExtraction(
                        chunk_id=chunk.chunk_id,
                        section_type=chunk.section_type,
                        confidence_score=0.0,
                    )

        await asyncio.gather(*(process(i, c) for i, c in enumerate(chunks)))
        return [r for r in results if r is not None]

    @llm_retry()
    async def _extract_chunk(self, chunk: SemanticChunk) -> ChunkExtraction:
        user_prompt = CHUNK_EXTRACTION_USER.format(
            section_type=chunk.section_type.value,
            section_title=chunk.section_title,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            chunk_text=chunk.content[:12000],
        )
        raw = await self._call_structured(
            system=CHUNK_EXTRACTION_SYSTEM,
            user=user_prompt,
            response_model=ChunkExtraction,
        )
        raw.chunk_id = chunk.chunk_id
        raw.section_type = chunk.section_type
        return raw

    async def merge_extractions(
        self,
        partials: list[ChunkExtraction],
        project_id: str,
        filename: str,
    ) -> ProjectKnowledge:
        if not partials:
            raise ExtractionError("No chunk extractions to merge")

        partial_json = json.dumps(
            [p.model_dump(mode="json") for p in partials],
            indent=2,
        )[:80000]

        try:
            merged = await self._merge_via_llm(
                partial_json=partial_json,
                project_id=project_id,
                filename=filename,
            )
        except Exception as e:
            logger.warning("llm_merge_failed_using_heuristic", error=str(e))
            merged = self._heuristic_merge(partials, project_id, filename)

        merged.project_id = project_id
        merged.extraction_metadata.source_chunk_ids = [p.chunk_id for p in partials]
        merged.extraction_metadata.model_version = self.deployment
        merged.extraction_metadata.schema_version = self.settings.schema_version
        return merged

    @llm_retry()
    async def _merge_via_llm(
        self,
        partial_json: str,
        project_id: str,
        filename: str,
    ) -> ProjectKnowledge:
        user_prompt = MERGE_EXTRACTION_USER.format(
            filename=filename,
            project_id=project_id,
            partial_json=partial_json,
        )
        return await self._call_structured(
            system=MERGE_EXTRACTION_SYSTEM,
            user=user_prompt,
            response_model=ProjectKnowledge,
        )

    async def _call_structured(
        self,
        system: str,
        user: str,
        response_model: type[T],
    ) -> T:
        schema = response_model.model_json_schema()
        response = await self.client.chat.completions.create(
            model=self.deployment,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "schema": schema,
                    "strict": False,
                },
            },
        )
        content = response.choices[0].message.content
        if not content:
            raise ExtractionError("Empty LLM response")
        try:
            data = json.loads(content)
            return response_model.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise ExtractionError(
                f"Failed to parse LLM output as {response_model.__name__}",
                {"error": str(e), "raw": content[:500]},
            ) from e

    def _heuristic_merge(
        self,
        partials: list[ChunkExtraction],
        project_id: str,
        filename: str,
    ) -> ProjectKnowledge:
        from app.schemas.extraction import (
            ArchitectureKnowledge,
            ExtractionMetadata,
            OrchestrationKnowledge,
            SourceDocument,
        )

        agents = []
        workflows = []
        tech: list[str] = []
        models: list[str] = []
        vdb: list[str] = []
        apis: list[str] = []
        outcomes: list[str] = []
        limitations: list[str] = []
        improvements: list[str] = []
        arch = ArchitectureKnowledge()
        orch = OrchestrationKnowledge()
        project_name = ""
        industry = ""
        business_problem = ""
        summary = ""
        workflow_desc = ""

        for p in partials:
            agents.extend(p.agents)
            workflows.extend(p.workflows)
            tech.extend(p.tech_stack)
            models.extend(p.models_used)
            vdb.extend(p.vector_databases)
            apis.extend(p.apis_used)
            outcomes.extend(p.business_outcomes)
            limitations.extend(p.limitations)
            improvements.extend(p.future_improvements)
            if p.project_name_hint and not project_name:
                project_name = p.project_name_hint
            if p.industry_hint and not industry:
                industry = p.industry_hint
            if p.business_problem and not business_problem:
                business_problem = p.business_problem
            if p.summary and len(p.summary) > len(summary):
                summary = p.summary
            if p.workflow_description:
                workflow_desc = p.workflow_description
            if p.architecture:
                if p.architecture.confidence_score >= arch.confidence_score:
                    arch = p.architecture
            if p.orchestration and p.orchestration.confidence_score >= orch.confidence_score:
                orch = p.orchestration

        confidences = [p.confidence_score for p in partials if p.confidence_score > 0]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.5

        return ProjectKnowledge(
            project_id=project_id,
            project_name=project_name or filename,
            industry=industry,
            business_problem=business_problem,
            summary=summary,
            agents=merge_agent_lists(agents),
            workflows=workflows,
            architecture=arch,
            orchestration=orch,
            tech_stack=dedupe_preserve_order(tech),
            models_used=dedupe_preserve_order(models),
            vector_databases=dedupe_preserve_order(vdb),
            apis_used=dedupe_preserve_order(apis),
            workflow_description=workflow_desc,
            business_outcomes=dedupe_preserve_order(outcomes),
            limitations=dedupe_preserve_order(limitations),
            future_improvements=dedupe_preserve_order(improvements),
            source_document=SourceDocument(filename=filename),
            extraction_metadata=ExtractionMetadata(
                confidence_score=avg_conf,
                source_chunk_ids=[p.chunk_id for p in partials],
                model_version=self.deployment,
            ),
        )
