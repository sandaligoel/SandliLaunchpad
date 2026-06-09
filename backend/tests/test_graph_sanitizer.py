"""Tests for graph_sanitizer."""

from schemas.architecture_spec import GraphDraft, GraphEdge, GraphNode
from services.graph_sanitizer import normalize_node_id, sanitize_graph


def test_removes_invalid_edges_and_self_loops():
    graph = GraphDraft(
        nodes=[
            GraphNode(id="a", label="A", type="gateway"),
            GraphNode(id="b", label="B", type="agent"),
        ],
        edges=[
            GraphEdge(from_id="a", to_id="b"),
            GraphEdge(from_id="b", to_id="missing"),
            GraphEdge(from_id="a", to_id="a"),
        ],
    )
    clean = sanitize_graph(graph)
    assert len(clean.nodes) == 2
    assert len(clean.edges) == 1
    assert clean.edges[0].from_id == "a"
    assert clean.edges[0].to_id == "b"


def test_breaks_backward_edge():
    graph = GraphDraft(
        nodes=[
            GraphNode(id="start", label="Start", type="gateway"),
            GraphNode(id="mid", label="Mid", type="agent"),
            GraphNode(id="end", label="End", type="agent"),
        ],
        edges=[
            GraphEdge(from_id="start", to_id="mid"),
            GraphEdge(from_id="end", to_id="start"),
            GraphEdge(from_id="mid", to_id="end"),
        ],
    )
    clean = sanitize_graph(graph)
    ids = {(e.from_id, e.to_id) for e in clean.edges}
    assert ("end", "start") not in ids
    assert ("start", "mid") in ids
    assert ("mid", "end") in ids


def test_normalize_node_id():
    assert normalize_node_id("Foo Bar!") == "foo-bar"


def test_adds_end_node_for_parallel_branches():
    """Quin + Eryl branches without merge get workflow-end."""
    graph = GraphDraft(
        nodes=[
            GraphNode(id="copilot-gateway", label="Copilot Gateway", type="gateway"),
            GraphNode(
                id="pipeline-intent-classifier",
                label="Pipeline Intent Classifier",
                type="agent",
            ),
            GraphNode(id="quin-sql-agent-chain", label="Quin SQL", type="agent"),
            GraphNode(id="eryl-semantic-rag-agent-chain", label="Eryl RAG", type="agent"),
        ],
        edges=[
            GraphEdge(from_id="copilot-gateway", to_id="pipeline-intent-classifier"),
            GraphEdge(from_id="pipeline-intent-classifier", to_id="quin-sql-agent-chain"),
            GraphEdge(
                from_id="pipeline-intent-classifier",
                to_id="eryl-semantic-rag-agent-chain",
            ),
        ],
    )
    clean = sanitize_graph(graph)
    end_nodes = [n for n in clean.nodes if n.label == "End" or n.id == "workflow-end"]
    assert len(end_nodes) == 1
    end_id = end_nodes[0].id
    targets = {e.to_id for e in clean.edges if e.from_id in ("quin-sql-agent-chain", "eryl-semantic-rag-agent-chain")}
    assert end_id in targets
