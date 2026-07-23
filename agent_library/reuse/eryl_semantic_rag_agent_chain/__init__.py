"""
Eryl Semantic RAG Agent Chain — frozen reuse package.

See agent.py for AssistantAgent definitions and ErylChainRunner entrypoint.
"""

from .agent import (
    ErylChainRunner,
    ENTRY_AGENT,
    EXIT_AGENTS,
    LLM_CONFIG,
    POST_GENERATION_EVALUATION_RUBRIC,
    build_agents,
    compute_post_generation_composite,
    generate_embeddings,
    route,
    search_client,
)

__all__ = [
    "ErylChainRunner",
    "build_agents",
    "route",
    "ENTRY_AGENT",
    "EXIT_AGENTS",
    "LLM_CONFIG",
    "POST_GENERATION_EVALUATION_RUBRIC",
    "compute_post_generation_composite",
    "generate_embeddings",
    "search_client",
]

__agent_name__ = "eryl_semantic_rag_agent_chain"
__version__ = "1.0.0"
