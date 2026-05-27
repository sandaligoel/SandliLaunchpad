"""Normalize and repair architecture flow graphs before Phase 3 / canvas render."""

from __future__ import annotations

import re
from collections import defaultdict, deque

from schemas.architecture_spec import GraphDraft, GraphEdge, GraphNode

_NODE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def normalize_node_id(raw: str) -> str:
    text = raw.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = text.strip("-") or "node"
    if not _NODE_ID_RE.match(text):
        text = re.sub(r"-+", "-", text).strip("-") or "node"
    return text


def _dedupe_nodes(nodes: list[GraphNode]) -> list[GraphNode]:
    seen: dict[str, GraphNode] = {}
    for node in nodes:
        nid = normalize_node_id(node.id)
        if nid in seen:
            existing = seen[nid]
            if not existing.label and node.label:
                seen[nid] = node.model_copy(update={"id": nid})
            continue
        seen[nid] = node.model_copy(update={"id": nid})
    return list(seen.values())


def _dedupe_edges(edges: list[GraphEdge]) -> list[GraphEdge]:
    seen: set[tuple[str, str]] = set()
    out: list[GraphEdge] = []
    for edge in edges:
        key = (edge.from_id, edge.to_id)
        if key in seen or edge.from_id == edge.to_id:
            continue
        seen.add(key)
        out.append(edge)
    return out


def _topo_order(node_ids: list[str], edges: list[GraphEdge]) -> list[str]:
    """Kahn topological sort; on cycles, break by dropping backward edges first."""
    ids = list(node_ids)
    if not ids:
        return []

    indegree = {nid: 0 for nid in ids}
    adj: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge.from_id not in indegree or edge.to_id not in indegree:
            continue
        adj[edge.from_id].append(edge.to_id)
        indegree[edge.to_id] += 1

    queue = deque([nid for nid in ids if indegree[nid] == 0])
    order: list[str] = []
    while queue:
        nid = queue.popleft()
        order.append(nid)
        for nxt in adj[nid]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)

    if len(order) == len(ids):
        return order

    # Cycle: keep edges that respect declaration order of nodes
    index = {nid: i for i, nid in enumerate(ids)}
    forward = [e for e in edges if index.get(e.from_id, 0) < index.get(e.to_id, 0)]
    return _topo_order(ids, forward) if forward != edges else ids


def _filter_forward_edges(
    node_ids: list[str], edges: list[GraphEdge]
) -> list[GraphEdge]:
    order = _topo_order(node_ids, edges)
    rank = {nid: i for i, nid in enumerate(order)}
    kept: list[GraphEdge] = []
    for edge in edges:
        if edge.from_id not in rank or edge.to_id not in rank:
            continue
        if rank[edge.from_id] < rank[edge.to_id]:
            kept.append(edge)
    return kept


def _undirected_components(
    node_ids: list[str], edges: list[GraphEdge]
) -> list[list[str]]:
    parent = {nid: nid for nid in node_ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for edge in edges:
        if edge.from_id in parent and edge.to_id in parent:
            union(edge.from_id, edge.to_id)

    groups: dict[str, list[str]] = defaultdict(list)
    for nid in node_ids:
        groups[find(nid)].append(nid)
    return list(groups.values())


def _connect_dangling_sinks(
    node_ids: list[str], edges: list[GraphEdge]
) -> list[GraphEdge]:
    """Link orphan exit nodes into the main downstream path."""
    if len(node_ids) <= 1:
        return edges

    out_degree = {nid: 0 for nid in node_ids}
    for e in edges:
        out_degree[e.from_id] = out_degree.get(e.from_id, 0) + 1

    sinks = [nid for nid in node_ids if out_degree.get(nid, 0) == 0]
    if len(sinks) <= 1:
        return edges

    order = _topo_order(node_ids, edges)
    rank = {nid: i for i, nid in enumerate(order)}

    def sink_priority(nid: str) -> tuple[int, int]:
        label_boost = 0
        if any(x in nid for x in ("output", "workbench", "end", "complete")):
            label_boost = 1
        return (label_boost, rank.get(nid, 0))

    primary = max(sinks, key=sink_priority)
    out = list(edges)
    for sid in sinks:
        if sid != primary:
            out.append(GraphEdge(from_id=sid, to_id=primary, label="flow"))
    return _dedupe_edges(out)


def _connect_components(
    nodes: list[GraphNode], edges: list[GraphEdge]
) -> list[GraphEdge]:
    if len(nodes) <= 1:
        return edges

    node_ids = [n.id for n in nodes]
    comps = _undirected_components(node_ids, edges)
    if len(comps) <= 1:
        return edges

    order = _topo_order(node_ids, edges)
    rank = {nid: i for i, nid in enumerate(order)}

    def comp_sort(comp: list[str]) -> int:
        return min(rank.get(nid, 9999) for nid in comp)

    comps.sort(key=comp_sort)
    out = list(edges)
    out_degree = defaultdict(int)
    in_degree = defaultdict(int)
    for e in out:
        out_degree[e.from_id] += 1
        in_degree[e.to_id] += 1

    for i in range(len(comps) - 1):
        left = comps[i]
        right = comps[i + 1]
        sink = max(left, key=lambda nid: (out_degree[nid], -rank.get(nid, 0)))
        source = min(right, key=lambda nid: (in_degree[nid], rank.get(nid, 9999)))
        bridge = GraphEdge(from_id=sink, to_id=source, label="flow")
        if sink != source:
            out.append(bridge)
            out_degree[sink] += 1
            in_degree[source] += 1

    return _dedupe_edges(out)


def _linear_chain_if_empty(nodes: list[GraphNode]) -> list[GraphEdge]:
    if len(nodes) < 2:
        return []
    edges: list[GraphEdge] = []
    for i in range(len(nodes) - 1):
        edges.append(
            GraphEdge(
                from_id=nodes[i].id,
                to_id=nodes[i + 1].id,
                label="next",
            )
        )
    return edges


def sanitize_graph(graph: GraphDraft) -> GraphDraft:
    """
    Repair a graph for canvas display: valid ids, forward-only edges, connected DAG.
    """
    nodes = _dedupe_nodes(graph.nodes)
    if not nodes:
        return GraphDraft(nodes=[], edges=[])

    node_ids = {n.id for n in nodes}
    edges = [
        GraphEdge(
            from_id=normalize_node_id(e.from_id),
            to_id=normalize_node_id(e.to_id),
            label=(e.label or "").strip() or None,
        )
        for e in graph.edges
        if normalize_node_id(e.from_id) in node_ids
        and normalize_node_id(e.to_id) in node_ids
    ]
    edges = _dedupe_edges(edges)
    node_ids = [n.id for n in nodes]
    edges = _filter_forward_edges(node_ids, edges)
    edges = _connect_components(nodes, edges)
    edges = _connect_dangling_sinks(node_ids, edges)

    if not edges and len(nodes) >= 2:
        edges = _linear_chain_if_empty(nodes)

    return GraphDraft(nodes=nodes, edges=edges)
