import type { Edge } from "@xyflow/react";
import type { ArchitecturePlan, ReuseDecisionType } from "@/api/affine/types";

export function syncFlowEdgesToPlan(
  plan: ArchitecturePlan,
  edges: Edge[],
): ArchitecturePlan {
  const graphEdges = edges.map((e) => ({
    from_id: String(e.source),
    to_id: String(e.target),
    label: typeof e.label === "string" ? e.label : undefined,
  }));
  return {
    ...plan,
    graph: { ...plan.graph, edges: graphEdges },
  };
}

export function updatePlanStep(
  plan: ArchitecturePlan,
  nodeId: string,
  patch: {
    node_label?: string;
    decision?: ReuseDecisionType;
    rationale?: string;
  },
): ArchitecturePlan {
  const reuse_decisions = plan.reuse_decisions.map((d) =>
    d.node_id === nodeId ? { ...d, ...patch } : d,
  );
  const nodes = plan.graph.nodes.map((n) =>
    n.id === nodeId && patch.node_label
      ? { ...n, label: patch.node_label }
      : n,
  );
  return {
    ...plan,
    reuse_decisions,
    graph: { ...plan.graph, nodes },
  };
}
