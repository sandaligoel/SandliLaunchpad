import type { ArchitecturePlan } from "@/types/plan";
import { buildGraphStructure, orderedAgents } from "@/lib/buildGraphStructure";
import { calculateLayout } from "@/layout/calculateLayout";

export interface GraphBuildResult {
  nodes: Awaited<ReturnType<typeof calculateLayout>>["nodes"];
  edges: ReturnType<typeof buildGraphStructure>["edges"];
  lanes: import("@/types/plan").FlowLane[];
  stats: {
    agents: number;
    reuse: number;
    adapt: number;
    build: number;
    parallelBranches: number;
  };
  layoutMeta?: Awaited<ReturnType<typeof calculateLayout>>["meta"];
}

export async function planToFlowGraph(plan: ArchitecturePlan): Promise<GraphBuildResult> {
  const structure = buildGraphStructure(plan);
  const { nodes, meta } = await calculateLayout(
    structure.nodes,
    structure.edges,
    structure.parallel
  );

  const agents = orderedAgents(plan);
  let reuse = 0,
    adapt = 0,
    build = 0;
  agents.forEach((a) => {
    if (a.reuse_decision === "reuse") reuse++;
    else if (a.reuse_decision === "adapt") adapt++;
    else build++;
  });

  return {
    nodes,
    edges: structure.edges,
    lanes: ["input", "orchestration", "execution", "merge", "hitl"],
    stats: {
      agents: agents.length,
      reuse,
      adapt,
      build,
      parallelBranches: structure.parallel?.branchIds.length ?? 0,
    },
    layoutMeta: meta,
  };
}

/** @deprecated sync stub — use planToFlowGraph */
export function planToFlowGraphSync(plan: ArchitecturePlan): GraphBuildResult {
  const structure = buildGraphStructure(plan);
  return {
    nodes: structure.nodes,
    edges: structure.edges,
    lanes: ["input", "orchestration", "execution", "merge", "hitl"],
    stats: {
      agents: 0,
      reuse: 0,
      adapt: 0,
      build: 0,
      parallelBranches: structure.parallel?.branchIds.length ?? 0,
    },
  };
}
