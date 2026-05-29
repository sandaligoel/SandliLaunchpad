import type { Edge, Node } from "@xyflow/react";
import type {
  ArchitecturePlan,
  FlowEdgeData,
  FlowLane,
  FlowNodeData,
  FlowNodeKind,
  GraphNode,
} from "@/types/plan";
import { mockRuntimeForNode } from "@/lib/mockRuntime";
import { getNodeReuseDecision } from "@/lib/planReuse";

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

function classifyAgentLane(label: string, desc: string): FlowLane {
  const t = `${label} ${desc}`.toLowerCase();
  if (t.includes("merge") || t.includes("aggregat") || t.includes("violation report"))
    return "merge";
  if (t.includes("gate") || t.includes("block") || t.includes("decision") || t.includes("score"))
    return "merge";
  if (t.includes("intake") || t.includes("reference")) return "input";
  return "execution";
}

function isMergeNode(n: GraphNode): boolean {
  const t = `${n.label} ${n.description || ""}`.toLowerCase();
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
  return t.includes("gate") || t.includes("block") || t.includes("until all checks");
}

function isStepNode(n: GraphNode): boolean {
  return (
    n.type === "agent" ||
    n.type === "custom" ||
    n.type === "gateway"
  );
}

/** Full left-to-right pipeline order (intake → orchestrator → steps → human). */
export function orderedPipelineSteps(plan: ArchitecturePlan): GraphNode[] {
  const nodes = plan.nodes || [];
  const edges = plan.edges || [];
  const entry = nodes.filter((n) => n.type === "data_store" || n.type === "api");
  const orch = nodes.find((n) => n.type === "orchestrator");
  const human = nodes.find((n) => n.type === "human");
  const steps = nodes.filter(isStepNode);

  const orderedSteps: GraphNode[] = [];
  const seen = new Set<string>();
  const walk = (nodeId: string) => {
    if (!nodeId || seen.has(nodeId)) return;
    seen.add(nodeId);
    const node = steps.find((n) => n.id === nodeId);
    if (node) orderedSteps.push(node);
    edges.filter((e) => e.source === nodeId).forEach((e) => walk(e.target));
  };

  if (orch) walk(orch.id);

  steps
    .sort((a, b) => {
      const ao = Number(a.metadata?.pipeline_order || a.layer || 0);
      const bo = Number(b.metadata?.pipeline_order || b.layer || 0);
      return ao - bo;
    })
    .forEach((a) => {
      if (!seen.has(a.id)) orderedSteps.push(a);
    });

  return [...entry, ...(orch ? [orch] : []), ...orderedSteps, ...(human ? [human] : [])];
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
  bridge: (from: string, to: string, label: string) => void
): void {
  const seq = orderedPipelineSteps(plan)
    .map((n) => n.id)
    .filter((id) => canvasNodeIds.has(id));

  for (let i = 0; i < seq.length - 1; i++) {
    const from = seq[i];
    const to = seq[i + 1];
    if (from === to) continue;
    if (!edgeExists(edges, from, to) && !hasPath(edges, from, to)) {
      bridge(from, to, "flow");
    }
  }

  for (const id of canvasNodeIds) {
    if (id.startsWith("__")) continue;
    const degree = edges.filter((e) => e.source === id || e.target === id).length;
    if (degree > 0) continue;
    const idx = seq.indexOf(id);
    if (idx > 0) bridge(seq[idx - 1], id, "flow");
    else if (idx >= 0 && seq.length > 1) bridge(id, seq[1], "flow");
  }
}

export function detectParallel(plan: ArchitecturePlan, agents: GraphNode[]): ParallelHint | null {
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
      forkAfterId = agents[0]?.id ?? null;
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
  return {
    id: node.id,
    type: kind,
    position: { x: 0, y: 0 },
    data: {
      kind,
      label: node.label,
      description: node.description,
      lane,
      reuse: getNodeReuseDecision(plan, node),
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

export function buildGraphStructure(plan: ArchitecturePlan): GraphStructure {
  const nodes: Node<FlowNodeData>[] = [];
  const edges: Edge<FlowEdgeData>[] = [];
  const agents = orderedAgents(plan);
  const parallel = detectParallel(plan, agents);
  const parallelSet = new Set(parallel?.branchIds ?? []);

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

  const entry = plan.nodes.filter((n) => n.type === "data_store" || n.type === "api");
  const orch = plan.nodes.find((n) => n.type === "orchestrator");
  const human = plan.nodes.find((n) => n.type === "human");

  for (const n of entry) nodes.push(toFlowNode(plan, n, "input", "input"));
  if (orch) nodes.push(toFlowNode(plan, orch, "orchestrator", "orchestration"));

  for (const a of agents) {
    let kind = agentKind(a.reuse_decision);
    let lane = classifyAgentLane(a.label, a.description || "");
    if (isMergeNode(a)) {
      kind = isDecisionNode(a) ? "decision" : "merge";
      lane = "merge";
    }
    const branchIdx = parallel?.branchIds.indexOf(a.id) ?? -1;
    nodes.push(
      toFlowNode(plan, a, kind, lane, {
        branchLabel: branchIdx >= 0 ? `Branch ${branchIdx + 1}` : undefined,
      })
    );
  }

  if (human) nodes.push(toFlowNode(plan, human, "human", "hitl"));

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

  if (human) {
    const mergeN = parallel?.mergeId;
    const lastExec = [...agents]
      .reverse()
      .find((a) => !parallelSet.has(a.id) && a.id !== mergeN);
    if (lastExec && !edges.some((e) => e.target === human.id)) {
      addEdge(lastExec.id, human.id, "retry", "escalate");
    } else if (mergeN && !edges.some((e) => e.target === human.id)) {
      addEdge(mergeN, human.id, "retry", "escalate");
    }
  }

  const canvasNodeIds = new Set(
    nodes.filter((n) => !n.id.startsWith("__")).map((n) => n.id)
  );
  ensurePipelineConnectivity(plan, canvasNodeIds, edges, (from, to, label) => {
    addEdge(from, to, "sequential", label);
  });

  return { nodes, edges, parallel };
}
