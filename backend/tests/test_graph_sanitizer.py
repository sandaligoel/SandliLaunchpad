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
