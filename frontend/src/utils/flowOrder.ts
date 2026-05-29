import type { GraphDraft } from "@/api/affine/types";

/**
 * Topological order for workflow list (sources → sinks).
 */
export function computeFlowOrder(graph: GraphDraft): string[] {
  const ids = graph.nodes.map((n) => n.id);
  const inDeg = new Map<string, number>();
  const adj = new Map<string, string[]>();

  for (const id of ids) {
    inDeg.set(id, 0);
    adj.set(id, []);
  }

  for (const e of graph.edges) {
    if (!adj.has(e.from_id) || !inDeg.has(e.to_id)) continue;
    adj.get(e.from_id)!.push(e.to_id);
    inDeg.set(e.to_id, (inDeg.get(e.to_id) ?? 0) + 1);
  }

  const queue = ids.filter((id) => (inDeg.get(id) ?? 0) === 0);
  if (queue.length === 0 && ids.length > 0) queue.push(ids[0]);

  const order: string[] = [];
  const seen = new Set<string>();

  while (queue.length > 0) {
    const id = queue.shift()!;
    if (seen.has(id)) continue;
    seen.add(id);
    order.push(id);
    for (const next of adj.get(id) ?? []) {
      inDeg.set(next, (inDeg.get(next) ?? 1) - 1);
      if ((inDeg.get(next) ?? 0) <= 0) queue.push(next);
    }
  }

  for (const id of ids) {
    if (!seen.has(id)) order.push(id);
  }

  return order;
}
