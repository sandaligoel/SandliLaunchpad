import type { Edge, Node } from "@xyflow/react";
import type {
  ArchitecturePlan,
  FlowEdgeData,
  FlowLane,
  FlowNodeData,
  FlowNodeKind,
  GraphNode,
} from "@/architecture-flow/types/plan";
import { mockRuntimeForNode } from "@/architecture-flow/lib/mockRuntime";
import { getNodeReuseDecision } from "@/architecture-flow/lib/planReuse";
import { resolveStepComponentKind } from "@/utils/stepComponentKind";

export interface ParallelHint {
  forkAfterId: string | null;
  branchIds: string[];
  mergeId: string | null;
}

function agentKind(reuse?: string): FlowNodeKind {
  if (reuse === "reuse") return "agent-reuse";
  if (reuse === "adapt") return "agent-adapt";
  return "agent-build";
}

function isIntakeLike(n: GraphNode): boolean {
  const t = `${n.label} ${n.description || ""}`.toLowerCase();
  return (
    n.type === "data_store" ||
    n.type === "api" ||
    t.includes("intake") ||
    t.includes("entrypoint") ||
    t.includes("upload")
  );
}

function classifyAgentLane(label: string, desc: string, nodeType?: string): FlowLane {
  const t = `${label} ${desc}`.toLowerCase();
  if (
    nodeType === "data_store" ||
    nodeType === "api" ||
    t.includes("intake") ||
    t.includes("entrypoint") ||
    t.includes("upload")
  ) {
    return "input";
  }
  if (t.includes("merge") || t.includes("aggregat") || t.includes("violation report"))
    return "merge";
  if (
    t.includes("routing gate") ||
    t.includes("blocking gate") ||
    t.includes("block/") ||
    (t.includes("decision") && !t.includes("gateway"))
  ) {
    return "merge";
  }
  if (t.includes("human") || t.includes("analyst review") || t.includes("hitl"))
    return "hitl";
  return "execution";
}

function isMergeNode(n: GraphNode): boolean {
  const t = `${n.label} ${n.description || ""}`.toLowerCase();
  if (isIntakeLike(n)) return false;
  return (
    t.includes("merge") ||
    t.includes("aggregat") ||
    t.includes("violation report") ||
    t.includes("gate export") ||
    t.includes("block/")
  );
}

function isDecisionNode(n: GraphNode): boolean {
  const t = `${n.label} ${n.description || ""}`.toLowerCase();
  if (isIntakeLike(n)) return false;
  return (
    t.includes("routing gate") ||
    t.includes("blocking gate") ||
    t.includes("block/") ||
    t.includes("until all checks")
  );
}

function isStepNode(n: GraphNode): boolean {
  return (
    n.type === "agent" ||
    n.type === "custom" ||
    n.type === "gateway"
  );
}

/** Topological order from plan edges (sources → sinks). */
function topoSortPlanNodes(
  nodes: GraphNode[],
  edges: { source: string; target: string }[],
): GraphNode[] {
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const ids = nodes.map((n) => n.id);
  const inDeg = new Map(ids.map((id) => [id, 0]));
  const adj = new Map(ids.map((id) => [id, [] as string[]]));

  for (const e of edges) {
    if (!byId.has(e.source) || !byId.has(e.target) || e.source === e.target) continue;
    adj.get(e.source)!.push(e.target);
    inDeg.set(e.target, (inDeg.get(e.target) ?? 0) + 1);
  }

  const queue = ids.filter((id) => (inDeg.get(id) ?? 0) === 0);
  if (queue.length === 0 && ids.length > 0) queue.push(ids[0]!);

  const order: string[] = [];
  const seen = new Set<string>();
  while (queue.length > 0) {
    const id = queue.shift()!;
    if (seen.has(id)) continue;
    seen.add(id);
    order.push(id);
    for (const nxt of adj.get(id) ?? []) {
      inDeg.set(nxt, (inDeg.get(nxt) ?? 0) - 1);
      if ((inDeg.get(nxt) ?? 0) <= 0) queue.push(nxt);
    }
  }
  for (const id of ids) {
    if (!seen.has(id)) order.push(id);
  }
  return order.map((id) => byId.get(id)!).filter(Boolean);
}

/** Full left-to-right pipeline order from graph edges (sources → sinks). */
export function orderedPipelineSteps(plan: ArchitecturePlan): GraphNode[] {
  const nodes = plan.nodes || [];
  const edges = plan.edges || [];
  if (nodes.length <= 1) return nodes;

  const topo = topoSortPlanNodes(nodes, edges);
  const topoRank = new Map(topo.map((n, i) => [n.id, i]));

  return [...nodes].sort((a, b) => {
    const topoA = topoRank.get(a.id) ?? 0;
    const topoB = topoRank.get(b.id) ?? 0;
    if (topoA !== topoB) return topoA - topoB;
    const intakeA = isIntakeLike(a) ? 0 : 1;
    const intakeB = isIntakeLike(b) ? 0 : 1;
    if (intakeA !== intakeB) return intakeA - intakeB;
    const ao = Number(a.metadata?.pipeline_order || a.layer || 0);
    const bo = Number(b.metadata?.pipeline_order || b.layer || 0);
    return ao - bo;
  });
}

export function orderedAgents(plan: ArchitecturePlan): GraphNode[] {
  return orderedPipelineSteps(plan).filter(isStepNode);
}

function edgeExists(edges: Edge<FlowEdgeData>[], source: string, target: string): boolean {
  return edges.some((e) => e.source === source && e.target === target);
}

function hasPath(edges: Edge<FlowEdgeData>[], from: string, to: string, maxHops = 16): boolean {
  const adj = new Map<string, string[]>();
  for (const e of edges) {
    if (!adj.has(e.source)) adj.set(e.source, []);
    adj.get(e.source)!.push(e.target);
  }
  const queue: [string, number][] = [[from, 0]];
  const seen = new Set([from]);
  while (queue.length) {
    const [id, depth] = queue.shift()!;
    if (id === to) return true;
    if (depth >= maxHops) continue;
    for (const nxt of adj.get(id) || []) {
      if (!seen.has(nxt)) {
        seen.add(nxt);
        queue.push([nxt, depth + 1]);
      }
    }
  }
  return false;
}

/** Bridge gaps when the planner omits edges between pipeline steps. */
function ensurePipelineConnectivity(
  plan: ArchitecturePlan,
  canvasNodeIds: Set<string>,
  edges: Edge<FlowEdgeData>[],
  bridge: (from: string, to: string, label: string) => void,
  parallel: ParallelHint | null = null,
): void {
  const branchSet = new Set(parallel?.branchIds ?? []);
  const forkId = parallel?.forkAfterId ?? null;

  const shouldSkipBridge = (from: string, to: string): boolean => {
    // Never chain parallel branch siblings into a false sequential path.
    if (branchSet.has(from) && branchSet.has(to)) return true;
    if (forkId && from === forkId && branchSet.has(to)) return true;
    return false;
  };

  const seq = orderedPipelineSteps(plan)
    .map((n) => n.id)
    .filter((id) => canvasNodeIds.has(id));

  for (let i = 0; i < seq.length - 1; i++) {
    const from = seq[i];
    const to = seq[i + 1];
    if (from === to || shouldSkipBridge(from, to)) continue;
    if (!edgeExists(edges, from, to) && !hasPath(edges, from, to)) {
      bridge(from, to, "flow");
    }
  }

  for (const id of canvasNodeIds) {
    if (id.startsWith("__")) continue;
    const degree = edges.filter((e) => e.source === id || e.target === id).length;
    if (degree > 0) continue;
    if (branchSet.has(id) && forkId) {
      bridge(forkId, id, "flow");
      continue;
    }
    const idx = seq.indexOf(id);
    if (idx > 0) {
      const from = seq[idx - 1];
      if (!shouldSkipBridge(from, id)) bridge(from, id, "flow");
    } else if (idx >= 0 && seq.length > 1) bridge(id, seq[1], "flow");
  }
}

export function detectParallel(plan: ArchitecturePlan, agents: GraphNode[]): ParallelHint | null {
  const agentIds = new Set(agents.map((a) => a.id));
  const planEdges = plan.edges || [];

  /** Fan-out in the saved plan (e.g. gateway → two agent chains). */
  for (const n of plan.nodes) {
    const targets = planEdges
      .filter((e) => e.source === n.id && agentIds.has(e.target))
      .map((e) => e.target);
    const branches = targets.filter((tid) => {
      const a = agents.find((x) => x.id === tid);
      return (
        a &&
        !isMergeNode(a) &&
        classifyAgentLane(a.label, a.description || "", a.type) === "execution"
      );
    });
    if (branches.length >= 2) {
      const mergeId = agents.find(isMergeNode)?.id ?? null;
      return {
        forkAfterId: n.id,
        branchIds: branches.slice(0, 4),
        mergeId,
      };
    }
  }

  const orchText = (plan.spec_summary?.orchestration_pattern || "").toLowerCase();
  const flowText = (plan.spec_summary?.flow_steps || "").toLowerCase();
  if (!orchText.includes("parallel") && !flowText.includes("parallel")) return null;

  const branchIds: string[] = [];
  let forkAfterId: string | null = null;
  let mergeId: string | null = null;

  for (const a of agents) {
    const t = `${a.label} ${a.description || ""}`.toLowerCase();
    if (isMergeNode(a)) mergeId = a.id;
    if (
      t.includes("parallel") ||
      t.includes("ocr") ||
      t.includes("white background") ||
      t.includes("lifestyle") ||
      t.includes("substantiation")
    ) {
      if (!branchIds.includes(a.id)) branchIds.push(a.id);
    }
  }

  if (branchIds.length < 2) {
    const exec = agents.filter(
      (a) => !isMergeNode(a) && classifyAgentLane(a.label, a.description || "") === "execution"
    );
    if (exec.length >= 2) {
      branchIds.push(exec[0].id, exec[1].id);
      const firstIdx = agents.findIndex((a) => a.id === exec[0].id);
      forkAfterId = firstIdx > 0 ? agents[firstIdx - 1]!.id : null;
    }
  } else {
    const firstBranchIdx = agents.findIndex((a) => a.id === branchIds[0]);
    if (firstBranchIdx > 0) forkAfterId = agents[firstBranchIdx - 1].id;
    else forkAfterId = plan.nodes.find((n) => n.type === "orchestrator")?.id ?? null;
  }

  if (!mergeId) {
    const m = agents.find(isMergeNode);
    if (m) mergeId = m.id;
  }

  if (branchIds.length >= 2) {
    return { forkAfterId, branchIds: branchIds.slice(0, 4), mergeId };
  }
  return null;
}

function toFlowNode(
  plan: ArchitecturePlan,
  node: GraphNode,
  kind: FlowNodeKind,
  lane: FlowLane,
  extra: Partial<FlowNodeData> = {}
): Node<FlowNodeData> {
  const reuse = getNodeReuseDecision(plan, node);
  const componentKind = resolveStepComponentKind(node, reuse);
  const catalogAgentName =
    node.catalog_agent_id ||
    (typeof node.metadata?.catalog_agent === "string" ? node.metadata.catalog_agent : undefined);

  return {
    id: node.id,
    type: kind,
    position: { x: 0, y: 0 },
    data: {
      kind,
      label: node.label,
      description: node.description,
      lane,
      reuse,
      componentKind,
      catalogAgentName,
      runtime: mockRuntimeForNode(node, plan),
      pipelineOrder: Number(node.metadata?.pipeline_order || node.layer || 0),
      capabilityId: node.metadata?.capability,
      ...extra,
    },
  };
}

export interface GraphStructure {
  nodes: Node<FlowNodeData>[];
  edges: Edge<FlowEdgeData>[];
  parallel: ParallelHint | null;
}

export function buildGraphStructure(
  plan: ArchitecturePlan,
  options?: { includeLaneChrome?: boolean },
): GraphStructure {
  const nodes: Node<FlowNodeData>[] = [];
  const edges: Edge<FlowEdgeData>[] = [];
  const pipelineOrder = orderedPipelineSteps(plan);
  const orderRank = new Map(pipelineOrder.map((n, i) => [n.id, i]));
  const agents = pipelineOrder.filter(isStepNode);
  const parallel = detectParallel(plan, agents);
  const parallelSet = new Set(parallel?.branchIds ?? []);

  if (options?.includeLaneChrome) {
    const laneKeys: FlowLane[] = ["input", "orchestration", "execution", "merge", "hitl"];
    for (const lane of laneKeys) {
      nodes.push({
        id: `__lane_${lane}`,
        type: "laneLabel",
        position: { x: 0, y: 0 },
        selectable: false,
        draggable: false,
        data: {
          kind: "lane-label",
          label:
            lane === "input"
              ? "INPUT"
              : lane === "orchestration"
                ? "ORCHESTRATION"
                : lane === "execution"
                  ? "EXECUTION"
                  : lane === "merge"
                    ? "MERGE & DECISION"
                    : "HUMAN-IN-THE-LOOP",
          lane,
          runtime: mockRuntimeForNode({ id: lane, type: "tool", label: "" }),
        },
      });
    }
  }

  const entry = pipelineOrder.filter(
    (n) => n.type === "data_store" || n.type === "api" || isIntakeLike(n),
  );
  const entryIds = new Set(entry.map((n) => n.id));
  const orch = pipelineOrder.find((n) => n.type === "orchestrator");

  const pushNode = (
    node: GraphNode,
    kind: FlowNodeKind,
    lane: FlowLane,
    extra: Partial<FlowNodeData> = {},
  ) => {
    const rank = orderRank.get(node.id) ?? 0;
    const withOrder = {
      ...node,
      metadata: { ...node.metadata, pipeline_order: String(rank + 1) },
      layer: rank + 1,
    };
    nodes.push(toFlowNode(plan, withOrder, kind, lane, extra));
  };

  for (const n of entry) pushNode(n, "input", "input");
  if (orch) pushNode(orch, "orchestrator", "orchestration");

  for (const n of pipelineOrder) {
    if (n.type === "human") {
      pushNode(n, "human", "hitl");
      continue;
    }
    if (!isStepNode(n) || entryIds.has(n.id)) continue;

    let kind = agentKind(n.reuse_decision);
    let lane = classifyAgentLane(n.label, n.description || "", n.type);
    if (isMergeNode(n)) {
      kind = isDecisionNode(n) ? "decision" : "merge";
      lane = "merge";
    }
    const branchIdx = parallel?.branchIds.indexOf(n.id) ?? -1;
    pushNode(n, kind, lane, {
      branchLabel: branchIdx >= 0 ? `Branch ${branchIdx + 1}` : undefined,
    });
  }

  const addEdge = (
    source: string,
    target: string,
    edgeKind: FlowEdgeData["edgeKind"],
    label?: string
  ) => {
    const id = `e_${source}_${target}_${edgeKind}`;
    if (edges.some((e) => e.id === id)) return;
    edges.push({
      id,
      source,
      target,
      type: "animated",
      data: { edgeKind, label, animated: edgeKind !== "data" },
    });
  };

  if (entry[0] && orch) addEdge(entry[0].id, orch.id, "data", "ingest");
  else if (entry[0] && agents[0]) addEdge(entry[0].id, agents[0].id, "data");

  if (parallel && parallel.branchIds.length >= 2) {
    const forkSource =
      parallel.forkAfterId ??
      orch?.id ??
      agents.find((a) => !parallelSet.has(a.id) && !isMergeNode(a))?.id;
    if (forkSource) {
      for (const bid of parallel.branchIds) {
        addEdge(forkSource, bid, "parallel", "branch");
      }
      if (parallel.mergeId) {
        for (const bid of parallel.branchIds) {
          addEdge(bid, parallel.mergeId, "merge", "join");
        }
      }
    }
  }

  for (const e of plan.edges) {
    if (parallelSet.has(e.source) && parallelSet.has(e.target)) continue;
    const kind: FlowEdgeData["edgeKind"] =
      e.type === "reads_from"
        ? "data"
        : e.label === "start"
          ? "sequential"
          : e.type === "escalates_to"
            ? "retry"
            : "sequential";
    if (!edges.some((x) => x.source === e.source && x.target === e.target)) {
      addEdge(e.source, e.target, kind, e.label);
    }
  }

  const canvasNodeIds = new Set(
    nodes.filter((n) => !n.id.startsWith("__")).map((n) => n.id)
  );
  ensurePipelineConnectivity(
    plan,
    canvasNodeIds,
    edges,
    (from, to, label) => {
      addEdge(from, to, "sequential", label);
    },
    parallel,
  );

  return { nodes, edges, parallel };
}
