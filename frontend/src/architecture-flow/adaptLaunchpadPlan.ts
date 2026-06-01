import type { ArchitecturePlan as GuruPlan, GraphNode as GuruNode } from "@/api/affine/types";
import type { AgentDef } from "@/types/api";
import {
  catalogInputs,
  catalogOutputs,
  findAgentDef,
  resolveCatalogAgentForNode,
} from "@/utils/stepIo";
import type {
  ArchitecturePlan as FlowPlan,
  GraphEdge,
  GraphNode,
  GraphNodeType,
  PlanReuseDecision,
} from "@/architecture-flow/types/plan";
import { computeFlowOrder } from "@/utils/flowOrder";

function mapNodeType(type: GuruNode["type"]): GraphNodeType {
  if (type === "gateway") return "api";
  if (type === "human") return "human";
  if (type === "agent") return "agent";
  return "custom";
}

function parseJsonList(raw: string | undefined): string[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (Array.isArray(parsed)) {
      return parsed.filter((x): x is string => typeof x === "string" && x.trim());
    }
  } catch {
    /* fallback below */
  }
  return raw.split("|||").map((s) => s.trim()).filter(Boolean);
}

function catalogIoForGuruNode(
  guru: GuruPlan,
  node: GuruNode,
  catalogAgents: AgentDef[],
): { inputs: string[]; outputs: string[] } {
  const savedIn = node.inputs?.filter((s) => s.trim()) ?? [];
  const savedOut = node.outputs?.filter((s) => s.trim()) ?? [];
  const agent = resolveCatalogAgentForNode(guru, node.id, catalogAgents);
  const fromCatalogIn = catalogInputs(agent);
  const fromCatalogOut = catalogOutputs(agent);
  return {
    inputs: savedIn.length ? savedIn : fromCatalogIn,
    outputs: savedOut.length ? savedOut : fromCatalogOut,
  };
}

function edgeLabelFor(
  guru: GuruPlan,
  fromId: string,
  catalogAgents: AgentDef[],
): string | undefined {
  const explicit = guru.graph.edges.find(
    (e) => e.from_id === fromId,
  )?.label;
  if (explicit?.trim()) return explicit.trim();

  const from = guru.graph.nodes.find((n) => n.id === fromId);
  if (!from) return undefined;
  const { outputs } = catalogIoForGuruNode(guru, from, catalogAgents);
  if (!outputs.length) return undefined;
  const text = outputs.slice(0, 2).join(" · ");
  return text.length > 72 ? `${text.slice(0, 69)}…` : text;
}

/** Map Launchpad API plan → dark architecture-flow graph plan. */
export function adaptGuruPlanToFlowPlan(
  guru: GuruPlan,
  catalogAgents: AgentDef[],
): FlowPlan {
  const flowOrder = computeFlowOrder(guru.graph);
  const orderRank = new Map(flowOrder.map((id, i) => [id, i]));

  const nodes: GraphNode[] = guru.graph.nodes.map((node, idx) => {
    const decision = guru.reuse_decisions.find((d) => d.node_id === node.id);
    const agent =
      findAgentDef(
        catalogAgents,
        node.agent_id ?? decision?.agent_id ?? null,
        decision?.agent_name ?? node.label,
      ) ?? resolveCatalogAgentForNode(guru, node.id, catalogAgents);
    const { inputs, outputs } = catalogIoForGuruNode(guru, node, catalogAgents);

    return {
      id: node.id,
      type: mapNodeType(node.type),
      label: node.label,
      description:
        node.description ??
        agent?.description ??
        ("function_summary" in (agent || {})
          ? (agent as { function_summary?: string }).function_summary
          : undefined) ??
        decision?.rationale,
      layer: (orderRank.get(node.id) ?? idx) + 1,
      catalog_agent_id: agent?.type ?? node.agent_id ?? undefined,
      reuse_decision: decision?.decision,
      metadata: {
        pipeline_order: String((orderRank.get(node.id) ?? idx) + 1),
        catalog_inputs: JSON.stringify(inputs),
        catalog_outputs: JSON.stringify(outputs),
        ...(node.input_json != null
          ? { input_json: JSON.stringify(node.input_json) }
          : {}),
        ...(node.output_json != null
          ? { output_json: JSON.stringify(node.output_json) }
          : {}),
      },
    };
  });

  const edges: GraphEdge[] = guru.graph.edges.map((e) => ({
    id: `e_${e.from_id}_${e.to_id}`,
    source: e.from_id,
    target: e.to_id,
    label: e.label?.trim() || edgeLabelFor(guru, e.from_id, catalogAgents) || "flow",
  }));

  const reuse_decisions: PlanReuseDecision[] = guru.reuse_decisions.map((d) => ({
    node_id: d.node_id,
    node_label: d.node_label,
    decision: d.decision,
    agent_id: d.agent_id ?? undefined,
    agent_name: d.agent_name ?? undefined,
    catalog_score: d.catalog_score ?? undefined,
    rationale: d.rationale,
  }));

  return {
    nodes,
    edges,
    reuse_decisions,
    catalog_matches: guru.catalog_matches.map((m) => ({
      agent_id: m.agent_id,
      name: m.name,
      score: m.score,
      matched_for: m.matched_for,
      function_summary: m.function_summary,
      origin_project: m.origin_project,
    })),
  };
}
