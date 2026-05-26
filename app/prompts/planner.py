"""Prompts for architecture planning and capability decomposition."""

CAPABILITY_DECOMPOSE_SYSTEM = """You build an agent pipeline for a diagram from an interview specification.

RULES:
1. agent_roles and flow_steps in the spec are AUTHORITATIVE — preserve their names and order.
2. Do NOT invent generic agents (ingest, classifier, OCR, staging) unless explicitly named in the spec.
3. Add at most 2 extra agents only if retrieval_required or knowledge_graph_scope clearly need a dedicated step and it is missing.
4. Each capability = one agent, snake_case id, pipeline_order starting at 1.
5. description = short human label taken from the spec (not a catalog product name).

Output JSON matching CapabilityListResult schema."""

CAPABILITY_DECOMPOSE_USER = """Interview specification (use this as source of truth):
{spec_json}

Return capabilities array matching the spec pipeline. Prefer agent_roles order, then flow_steps for any gaps."""

FLOW_ALIGN_SYSTEM = """You align an architecture pipeline to an interview spec.

The spec's agent_roles and flow_steps define the real pipeline. Output exactly those agents in execution order.

RULES:
1. Minimum 3, maximum 14 capabilities.
2. Do not add boilerplate agents not mentioned in the spec.
3. description must match spec wording (e.g. "Shelf vision / detection agent", "Compliance checker").

Output JSON matching CapabilityListResult schema."""

FLOW_ALIGN_USER = """Specification:
{spec_json}

Return the aligned capabilities array."""

PLANNER_NARRATIVE_SYSTEM = """Write a brief architecture flow narrative (2 short paragraphs).

Describe pipeline order using the same agent names from the spec, orchestration pattern, and catalog reuse. No security topics."""

PLANNER_NARRATIVE_USER = """Spec: {spec_summary}

Reuse decisions: {reuse_json}

Graph: {node_count} components, {edge_count} links

Write narrative."""
