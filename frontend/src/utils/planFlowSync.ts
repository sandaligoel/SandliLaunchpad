import type { Edge } from "@xyflow/react";
import type { ArchitecturePlan, ReuseDecisionType } from "@/api/affine/types";
import { sanitizeGraphDraft } from "@/utils/graphSanitize";

export function syncFlowEdgesToPlan(
  plan: ArchitecturePlan,
  edges: Edge[],
): ArchitecturePlan {
  const graphEdges = edges.map((e) => ({
    from_id: String(e.source),
    to_id: String(e.target),
    label: typeof e.label === "string" ? e.label : undefined,
  }));
  const graph = sanitizeGraphDraft({
    ...plan.graph,
    edges: graphEdges,
  });
  return {
    ...plan,
    graph,
  };
}

export function updatePlanStep(
  plan: ArchitecturePlan,
  nodeId: string,
  patch: {
    node_label?: string;
    decision?: ReuseDecisionType;
    rationale?: string;
    inputs?: string[];
    outputs?: string[];
    description?: string;
    input_json?: Record<string, unknown> | null;
    output_json?: Record<string, unknown> | null;
  },
): ArchitecturePlan {
  const reuse_decisions = plan.reuse_decisions.map((d) =>
    d.node_id === nodeId ? { ...d, ...patch } : d,
  );
  const nodes = plan.graph.nodes.map((n) => {
    if (n.id !== nodeId) return n;
    return {
      ...n,
      ...(patch.node_label ? { label: patch.node_label } : {}),
      ...(patch.inputs !== undefined ? { inputs: patch.inputs } : {}),
      ...(patch.outputs !== undefined ? { outputs: patch.outputs } : {}),
      ...(patch.description !== undefined
        ? { description: patch.description }
        : {}),
      ...(patch.input_json !== undefined ? { input_json: patch.input_json } : {}),
      ...(patch.output_json !== undefined ? { output_json: patch.output_json } : {}),
    };
  });
  return {
    ...plan,
    reuse_decisions,
    graph: { ...plan.graph, nodes },
  };
}
