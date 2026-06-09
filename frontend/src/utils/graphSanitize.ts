import type { GraphDraft, GraphEdge } from "@/api/affine/types";

function normalizeId(raw: string): string {
  return raw
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, "")
    .replace(/[\s_]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "") || "node";
}

function topoOrder(nodeIds: string[], edges: GraphEdge[]): string[] {
  const indegree = new Map(nodeIds.map((id) => [id, 0]));
  const adj = new Map<string, string[]>();
  for (const id of nodeIds) adj.set(id, []);
  for (const e of edges) {
    if (!indegree.has(e.from_id) || !indegree.has(e.to_id)) continue;
    adj.get(e.from_id)!.push(e.to_id);
    indegree.set(e.to_id, (indegree.get(e.to_id) ?? 0) + 1);
  }
  const queue = nodeIds.filter((id) => (indegree.get(id) ?? 0) === 0);
  const order: string[] = [];
  while (queue.length > 0) {
    const id = queue.shift()!;
    order.push(id);
    for (const nxt of adj.get(id) ?? []) {
      const d = (indegree.get(nxt) ?? 0) - 1;
      indegree.set(nxt, d);
      if (d === 0) queue.push(nxt);
    }
  }
  return order.length === nodeIds.length ? order : nodeIds;
}

/** Client-side repair so canvas arrows always point forward. */
export function sanitizeGraphDraft(graph: GraphDraft): GraphDraft {
  const nodeMap = new Map<string, (typeof graph.nodes)[0]>();
  for (const node of graph.nodes) {
    const id = normalizeId(node.id);
    if (!nodeMap.has(id)) {
      nodeMap.set(id, { ...node, id });
    }
  }
  const nodes = [...nodeMap.values()];
  const nodeIds = new Set(nodes.map((n) => n.id));

  const rawEdges: GraphEdge[] = [];
  const seen = new Set<string>();
  for (const e of graph.edges) {
    const from_id = normalizeId(e.from_id);
    const to_id = normalizeId(e.to_id);
    if (!nodeIds.has(from_id) || !nodeIds.has(to_id) || from_id === to_id) continue;
    const key = `${from_id}->${to_id}`;
    if (seen.has(key)) continue;
    seen.add(key);
    rawEdges.push({
      from_id,
      to_id,
      label: e.label?.trim() || undefined,
    });
  }

  const order = topoOrder(
    nodes.map((n) => n.id),
    rawEdges,
  );
  const rank = new Map(order.map((id, i) => [id, i]));
  let edges = rawEdges.filter(
    (e) => (rank.get(e.from_id) ?? 0) < (rank.get(e.to_id) ?? 0),
  );

  if (edges.length === 0 && nodes.length >= 2) {
    edges = nodes.slice(0, -1).map((n, i) => ({
      from_id: n.id,
      to_id: nodes[i + 1]!.id,
      label: "next",
    }));
  }

  const withEnd = ensureExitNode(nodes, edges);

  const bridged = bridgeHumanGates(withEnd.nodes, withEnd.edges, order);

  const endEdges = connectDanglingSinks(
    bridged.nodes.map((n) => n.id),
    bridged.edges,
    rank,
  );

  return { nodes: bridged.nodes, edges: endEdges };
}

function isHumanNode(node: GraphDraft["nodes"][number]): boolean {
  const blob = `${node.id} ${node.label} ${node.type}`.toLowerCase();
  return node.type === "human" || /\b(analyst|human|hitl|review)\b/.test(blob);
}

/** Wire human-in-the-loop steps to the next pipeline node when the planner omits the edge. */
function bridgeHumanGates(
  nodes: GraphDraft["nodes"],
  edges: GraphEdge[],
  order: string[],
): GraphDraft {
  const nodeIds = new Set(nodes.map((n) => n.id));
  const rank = new Map(order.map((id, i) => [id, i]));
  const seen = new Set(edges.map((e) => `${e.from_id}->${e.to_id}`));
  const out = [...edges];

  for (const node of nodes) {
    if (!isHumanNode(node)) continue;
    const r = rank.get(node.id);
    if (r == null) continue;
    const successors = order.filter((id) => (rank.get(id) ?? 0) > r && nodeIds.has(id));
    const next = successors[0];
    if (!next) continue;
    const key = `${node.id}->${next}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({ from_id: node.id, to_id: next, label: "flow" });
  }

  return { nodes, edges: out };
}

function isExitNode(node: GraphDraft["nodes"][number]): boolean {
  const blob = `${node.id} ${node.label} ${node.description ?? ""}`.toLowerCase();
  return (
    blob.includes("workflow-end") ||
    blob.includes("copilot-response") ||
    node.label.trim().toLowerCase() === "end"
  );
}

function ensureExitNode(
  nodes: GraphDraft["nodes"],
  edges: GraphEdge[],
): GraphDraft {
  if (nodes.length < 2) return { nodes, edges };

  const nodeIds = new Set(nodes.map((n) => n.id));
  const outDegree = new Map([...nodeIds].map((id) => [id, 0]));
  for (const e of edges) {
    outDegree.set(e.from_id, (outDegree.get(e.from_id) ?? 0) + 1);
  }

  const sinks = [...nodeIds].filter((id) => (outDegree.get(id) ?? 0) === 0);
  if (sinks.length <= 1) return { nodes, edges };

  const existingExit = nodes.find(isExitNode);
  if (existingExit && sinks.includes(existingExit.id)) {
    const endId = existingExit.id;
    const seen = new Set(edges.map((e) => `${e.from_id}->${e.to_id}`));
    const newEdges = [...edges];
    for (const sid of sinks) {
      if (sid === endId) continue;
      const key = `${sid}->${endId}`;
      if (!seen.has(key)) {
        seen.add(key);
        newEdges.push({ from_id: sid, to_id: endId, label: "answer" });
      }
    }
    return { nodes, edges: newEdges };
  }

  const endId = "workflow-end";
  const newNodes = [...nodes];
  if (!nodeIds.has(endId)) {
    newNodes.push({
      id: endId,
      label: "End",
      type: "gateway",
      description: "Final copilot response returned to the user.",
    });
  }

  const seen = new Set(edges.map((e) => `${e.from_id}->${e.to_id}`));
  const newEdges = [...edges];
  for (const sid of sinks) {
    if (sid === endId) continue;
    const key = `${sid}->${endId}`;
    if (!seen.has(key)) {
      seen.add(key);
      newEdges.push({ from_id: sid, to_id: endId, label: "answer" });
    }
  }

  return { nodes: newNodes, edges: newEdges };
}

function connectDanglingSinks(
  nodeIds: string[],
  edges: GraphEdge[],
  rank: Map<string, number>,
): GraphEdge[] {
  const outDegree = new Map(nodeIds.map((id) => [id, 0]));
  for (const e of edges) {
    outDegree.set(e.from_id, (outDegree.get(e.from_id) ?? 0) + 1);
  }
  const sinks = nodeIds.filter((id) => (outDegree.get(id) ?? 0) === 0);
  if (sinks.length <= 1) return edges;

  const sinkPriority = (id: string) => {
    const boost = /output|workbench|end|complete/i.test(id) ? 1 : 0;
    return boost * 1000 + (rank.get(id) ?? 0);
  };
  const exitSink = sinks.find((id) => /workflow-end|copilot-response|^end$/i.test(id));
  const primary = exitSink ?? sinks.reduce((a, b) => (sinkPriority(a) >= sinkPriority(b) ? a : b));
  const seen = new Set(edges.map((e) => `${e.from_id}->${e.to_id}`));
  const out = [...edges];
  for (const sid of sinks) {
    if (sid === primary) continue;
    const key = `${sid}->${primary}`;
    if (!seen.has(key)) {
      seen.add(key);
      out.push({ from_id: sid, to_id: primary, label: exitSink ? "answer" : "flow" });
    }
  }
  return out;
}
