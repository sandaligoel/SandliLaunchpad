"""OData filter and hybrid search query construction."""

from __future__ import annotations

from app.schemas.search import EntityType, SearchFilter, SearchMode


class QueryBuilder:
    """Builds Azure AI Search OData filters and search options."""

    @staticmethod
    def build_filter(filters: SearchFilter | None) -> str | None:
        if not filters:
            return None
        clauses: list[str] = []

        if filters.entity_types:
            type_exprs = [f"entity_type eq '{t.value}'" for t in filters.entity_types]
            clauses.append(f"({' or '.join(type_exprs)})")

        if filters.industry:
            clauses.append(f"industry eq '{_escape(filters.industry)}'")

        if filters.cloud_provider:
            clauses.append(f"cloud_provider eq '{_escape(filters.cloud_provider)}'")

        if filters.retrieval_used is not None:
            clauses.append(f"retrieval_used eq {str(filters.retrieval_used).lower()}")

        if filters.project_id:
            clauses.append(f"project_id eq '{_escape(filters.project_id)}'")

        if filters.source_filename:
            clauses.append(f"source_filename eq '{_escape(filters.source_filename)}'")

        if filters.min_confidence is not None:
            clauses.append(f"confidence_score ge {filters.min_confidence}")

        if filters.models_used:
            model_clauses = [
                f"models_used/any(m: m eq '{_escape(m)}')" for m in filters.models_used
            ]
            clauses.append(f"({' or '.join(model_clauses)})")

        return " and ".join(clauses) if clauses else None

    @staticmethod
    def agent_filter_extras(
        base: SearchFilter | None,
        agent_name_contains: str | None,
        tools_used: list[str] | None,
    ) -> str | None:
        f = base or SearchFilter()
        entity_types = [EntityType.AGENT]
        merged = f.model_copy(update={"entity_types": entity_types})
        clauses = []
        base_filter = QueryBuilder.build_filter(merged)
        if base_filter:
            clauses.append(f"({base_filter})")
        if agent_name_contains:
            safe = _escape(agent_name_contains)
            clauses.append(f"search.ismatch('{safe}*', 'agent_name')")
        if tools_used:
            tool_exprs = [
                f"tools_used/any(t: t eq '{_escape(t)}')" for t in tools_used
            ]
            clauses.append(f"({' or '.join(tool_exprs)})")
        return " and ".join(clauses) if clauses else None

    @staticmethod
    def architecture_filter_extras(
        base: SearchFilter | None,
        pattern: str | None,
        framework: str | None,
    ) -> str | None:
        f = base or SearchFilter()
        merged = f.model_copy(update={"entity_types": [EntityType.ARCHITECTURE]})
        clauses = []
        base_filter = QueryBuilder.build_filter(merged)
        if base_filter:
            clauses.append(f"({base_filter})")
        if pattern:
            clauses.append(f"architecture_pattern eq '{_escape(pattern)}'")
        if framework:
            clauses.append(f"orchestration_framework eq '{_escape(framework)}'")
        return " and ".join(clauses) if clauses else None

    @staticmethod
    def select_fields(include_payload: bool) -> list[str]:
        fields = [
            "id", "entity_type", "project_id", "project_name", "title",
            "content", "agent_name", "architecture_pattern", "cloud_provider",
            "tech_stack", "models_used", "confidence_score",
        ]
        if include_payload:
            fields.append("structured_payload")
        return fields

    @staticmethod
    def search_type(mode: SearchMode) -> str | None:
        if mode == SearchMode.SEMANTIC:
            return "semantic"
        return "simple"


def _escape(value: str) -> str:
    return value.replace("'", "''")
