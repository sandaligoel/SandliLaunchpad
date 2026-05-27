"""Per-slot guidance for flow + technical architecture interview (plain language)."""

SLOT_DEEP_GUIDANCE: dict[str, str] = {
    "flow_steps": "Ask what happens first, next, and last — like a simple checklist from start to finish.",
    "agent_roles": "Ask what each automated step does, in order — use job titles like 'reads documents' or 'approves results' (never 'helper').",
    "orchestration_pattern": "Ask whether steps run one-by-one, some at the same time, or with a coordinator in the middle.",
    "data_sources": "Ask where information comes from (files, photos, existing software).",
    "data_volume_scale": "Ask roughly how much work per month and how busy it gets.",
    "retrieval_required": "Ask whether the system needs to search older documents to answer questions.",
    "knowledge_graph_scope": "Ask whether related people, companies, or items need to be linked together.",
    "agent_tools": "Ask what kinds of tools are needed (read documents, read images, search files).",
    "model_constraints": "Ask which AI the organization allows — keep it simple.",
    "integrations": "Ask which existing business systems must be connected.",
    "deployment_target": "Ask where the solution should run (cloud vs existing servers).",
    "cloud_provider": "Ask which cloud the organization uses or prefers.",
    "human_in_the_loop": "Ask when a person must review or approve before finishing.",
    "failure_escalation": "Ask what should happen when a step fails (retry, alert a person, hold the case).",
}

