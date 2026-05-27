"""Versioned LLM prompts for grounded architecture extraction."""

SCHEMA_VERSION = "1.0.0"

CHUNK_EXTRACTION_SYSTEM = """You are an enterprise AI systems architect analyst.
Your task is to extract structured AI architecture knowledge from document chunks.

CRITICAL RULES:
1. Extract ONLY information explicitly stated or strongly implied in the provided text.
2. Do NOT invent agents, tools, models, or deployments not mentioned.
3. Use empty strings and empty lists for unknown fields.
4. Include short verbatim evidence_quotes (max 15 words each) for non-trivial claims.
5. Assign confidence_score between 0.0 and 1.0 based on textual evidence strength.
6. For agents, each distinct agent role mentioned should be a separate entry.
7. Normalize technology names (e.g., "GPT 4" -> "GPT-4", "Azure OpenAI" consistent casing).

You output valid JSON matching the provided schema."""

CHUNK_EXTRACTION_USER = """Extract AI architecture knowledge from this document chunk.

Section type hint: {section_type}
Section title: {section_title}
Pages: {page_start}-{page_end}

--- CHUNK TEXT ---
{chunk_text}
--- END CHUNK TEXT ---

Return JSON only."""

MERGE_EXTRACTION_SYSTEM = """You are an enterprise AI systems architect consolidating partial extractions
from multiple document sections into a single canonical project knowledge record.

CRITICAL RULES:
1. Merge duplicate agents by name (case-insensitive).
2. Prefer higher-confidence values when fields conflict.
3. Do NOT add information not supported by the partial extractions.
4. Synthesize relationships between agents, tools, APIs, and workflows when evident.
5. Produce a coherent project_name — use the most specific name found.
6. Assign overall extraction_metadata.confidence_score as weighted average of evidence.

Output valid JSON matching the ProjectKnowledge schema."""

MERGE_EXTRACTION_USER = """Consolidate these partial extractions from document "{filename}" into one ProjectKnowledge record.

Project ID (use exactly): {project_id}

--- PARTIAL EXTRACTIONS ---
{partial_json}
--- END ---

Return complete ProjectKnowledge JSON."""

SECTION_CLASSIFICATION_KEYWORDS: dict[str, list[str]] = {
    "agent": [
        "agent", "assistant", "bot", "copilot", "orchestrator",
        "sub-agent", "subagent", "specialist", "role",
    ],
    "architecture": [
        "architecture", "system design", "component", "microservice",
        "pattern", "high-level", "infrastructure",
    ],
    "workflow": [
        "workflow", "pipeline", "process flow", "sequence",
        "step-by-step", "orchestration flow", "data flow",
    ],
    "tech_stack": [
        "tech stack", "technology", "framework", "library",
        "stack", "tools used", "platform",
    ],
    "deployment": [
        "deployment", "hosting", "cloud", "kubernetes", "aks",
        "container", "ci/cd", "production",
    ],
    "use_case": [
        "use case", "business case", "problem statement",
        "objective", "goal", "requirement",
    ],
    "constraints": [
        "constraint", "limitation", "latency", "sla",
        "compliance", "security requirement",
    ],
    "integration": [
        "integration", "api", "connector", "webhook",
        "third-party", "external system",
    ],
    "project_overview": [
        "executive summary", "overview", "introduction",
        "project", "solution", "background",
    ],
}
