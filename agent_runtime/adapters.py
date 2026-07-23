"""Pure I/O shape adapters between workflow graph fields and reuse agent contracts."""

from __future__ import annotations

from typing import Any


DEFAULT_ANALYSIS_TYPE = "Semantic-based"
DEFAULT_RETRIEVAL_STRATEGY = "vector"


def adapt_graph_input_to_chain(payload: dict[str, Any]) -> dict[str, Any]:
    """Map workflow graph inputs to ErylChainRunner.run kwargs."""
    user_question = (
        payload.get("user_question")
        or payload.get("initial_question")
        or payload.get("question")
        or ""
    )
    if not str(user_question).strip():
        raise ValueError("user_question or initial_question is required")

    chain_input: dict[str, Any] = {
        "initial_question": str(user_question).strip(),
        "analysis_type": payload.get("analysis_type") or DEFAULT_ANALYSIS_TYPE,
    }
    if payload.get("sql_query") is not None:
        chain_input["sql_query"] = payload["sql_query"]
    if payload.get("sql_answer") is not None:
        chain_input["sql_answer"] = payload["sql_answer"]
    transformed = payload.get("transformed_query") or payload.get("updated_question")
    if transformed is not None:
        chain_input["updated_question"] = transformed
    return chain_input


def adapt_chain_output_to_node(node_id: str, chain_result: dict[str, Any]) -> dict[str, Any]:
    """Map ErylChainRunner.run output to per-node graph output contracts."""
    updated_question = chain_result.get("updated_question") or ""
    llm_answer = chain_result.get("llm_answer") or ""
    analysis_type = chain_result.get("analysis_type") or DEFAULT_ANALYSIS_TYPE

    if node_id == "query-transformer":
        return {"transformed_query": updated_question or chain_result.get("initial_question", "")}

    if node_id == "eryl-selector":
        return {
            "retrieval_strategy": DEFAULT_RETRIEVAL_STRATEGY,
            "routing_hints": {
                "strategy": DEFAULT_RETRIEVAL_STRATEGY,
                "updated_question": updated_question,
                "analysis_type": analysis_type,
            },
        }

    if node_id == "retriever":
        passages = chain_result.get("retrieved_passages")
        if passages is None:
            passages = []
        citations = chain_result.get("citations")
        if citations is None:
            citations = []
        return {"retrieved_passages": passages, "citations": citations}

    if node_id == "llm-answer-maker":
        return {"draft_answer": llm_answer}

    if node_id == "critic":
        confidence = chain_result.get("confidence_score")
        if confidence is None:
            confidence = chain_result.get("composite_score", 0.0)
        return {"final_answer": llm_answer, "confidence_score": confidence}

    return dict(chain_result)


def adapt_dry_run_node_output(node_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Shape dry-run outputs from real supplied inputs (no external I/O)."""
    user_question = (
        payload.get("user_question")
        or payload.get("initial_question")
        or payload.get("question")
        or ""
    ).strip()
    transformed = payload.get("transformed_query") or user_question

    if node_id == "query-transformer":
        return {"transformed_query": transformed}

    if node_id == "eryl-selector":
        return {
            "retrieval_strategy": DEFAULT_RETRIEVAL_STRATEGY,
            "routing_hints": {"strategy": DEFAULT_RETRIEVAL_STRATEGY, "question": transformed},
        }

    if node_id == "retriever":
        return {"retrieved_passages": [], "citations": []}

    if node_id == "llm-answer-maker":
        return {"draft_answer": ""}

    if node_id == "critic":
        return {"final_answer": "", "confidence_score": 0.0}

    return {}


def merge_node_output_into_state(state: dict[str, Any], node_id: str, node_output: dict[str, Any]) -> None:
    """Accumulate node outputs for downstream adapter consumption."""
    state.setdefault("node_outputs", {})[node_id] = node_output
    state.update(node_output)


def build_terminal_payload(state: dict[str, Any]) -> dict[str, Any]:
    """Return the workflow terminal payload from accumulated state."""
    critic_out = (state.get("node_outputs") or {}).get("critic", {})
    payload = {
        "final_answer": critic_out.get("final_answer") or state.get("final_answer", ""),
        "confidence_score": critic_out.get("confidence_score") or state.get("confidence_score", 0.0),
        "transformed_query": state.get("transformed_query", ""),
        "analysis_type": state.get("analysis_type", DEFAULT_ANALYSIS_TYPE),
        "node_outputs": state.get("node_outputs", {}),
    }
    if state.get("dry_run"):
        payload["dry_run"] = True
    return payload
