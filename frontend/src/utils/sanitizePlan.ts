import type { ArchitecturePlan } from "@/api/affine/types";
import { sanitizeGraphDraft } from "@/utils/graphSanitize";

/** Repair graph edges/nodes before canvas layout (fixes cycles from older API plans). */
export function sanitizeArchitecturePlan(plan: ArchitecturePlan): ArchitecturePlan {
  const graph = sanitizeGraphDraft(plan.graph);
  const nodeIds = new Set(graph.nodes.map((n) => n.id));
  const reuse_decisions = plan.reuse_decisions
    .filter((d) => nodeIds.has(d.node_id))
    .map((d) => {
      const node = graph.nodes.find((n) => n.id === d.node_id);
      return node ? { ...d, node_label: node.label } : d;
    });

  for (const node of graph.nodes) {
    if (!reuse_decisions.some((d) => d.node_id === node.id)) {
      reuse_decisions.push({
        node_id: node.id,
        node_label: node.label,
        decision: node.agent_id ? "reuse" : "build",
        agent_id: node.agent_id,
        agent_name: null,
        rationale: "Auto-filled for graph step.",
      });
    }
  }

  return { ...plan, graph, reuse_decisions };
}
