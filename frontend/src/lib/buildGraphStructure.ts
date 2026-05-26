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

export function orderedAgents(plan: ArchitecturePlan): GraphNode[] {
  const agents = plan.nodes.filter((n) => n.type === "agent");
  const edges = plan.edges || [];
  const ordered: GraphNode[] = [];
  const seen = new Set<string>();

  const orch = plan.nodes.find((n) => n.type === "orchestrator");
  const walk = (id: string) => {
    if (!id || seen.has(id)) return;
    const node = agents.find((a) => a.id === id);
    if (node) {
      seen.add(id);
      ordered.push(node);
    }
    edges
      .filter(
        (e) =>
          e.source === id &&
          (e.type === "invokes" || e.type === "produces" || e.label === "flow")
      )
      .forEach((e) => walk(e.target));
  };
  if (orch) walk(orch.id);

  agents
    .sort((a, b) => {
      const ao = Number(a.metadata?.pipeline_order || a.layer || 0);
      const bo = Number(b.metadata?.pipeline_order || b.layer || 0);
      return ao - bo;
    })
    .forEach((a) => {
      if (!seen.has(a.id)) ordered.push(a);
    });

  return ordered;
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
      reuse: node.reuse_decision,
      runtime: mockRuntimeForNode(node),
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

  for (const n of entry) nodes.push(toFlowNode(n, "input", "input"));
  if (orch) nodes.push(toFlowNode(orch, "orchestrator", "orchestration"));

  for (const a of agents) {
    let kind = agentKind(a.reuse_decision);
    let lane = classifyAgentLane(a.label, a.description || "");
    if (isMergeNode(a)) {
      kind = isDecisionNode(a) ? "decision" : "merge";
      lane = "merge";
    }
    const branchIdx = parallel?.branchIds.indexOf(a.id) ?? -1;
    nodes.push(
      toFlowNode(a, kind, lane, {
        branchLabel: branchIdx >= 0 ? `Branch ${branchIdx + 1}` : undefined,
      })
    );
  }

  if (human) nodes.push(toFlowNode(human, "human", "hitl"));

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

  return { nodes, edges, parallel };
}
