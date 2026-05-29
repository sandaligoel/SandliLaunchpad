import type { CatalogAgentRecord } from "@/api/affine/catalog";
import type { AgentDef } from "@/types/api";
import type {
  ArchitecturePlan,
  CatalogMatch,
  GraphNode,
  ReuseDecision,
} from "@/api/affine/types";
import { computeFlowOrder } from "@/utils/flowOrder";
import { updatePlanStep } from "@/utils/planFlowSync";

export type CatalogLike = CatalogAgentRecord | AgentDef;

const ENTRY_INPUTS = ["Workflow entry (user request or trigger)"];

const GATEWAY_OUTPUTS = [
  "Workflow trigger payload",
  "Routed items to downstream steps",
];
const HUMAN_OUTPUTS = [
  "Human review decision",
  "Approved / rejected outcome for next step",
];

function slugify(text: string): string {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, "")
    .replace(/[\s_]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

function tokenSet(text: string): Set<string> {
  return new Set(
    text
      .toLowerCase()
      .split(/[^a-z0-9]+/)
      .filter((t) => t.length >= 3),
  );
}

export function findAgentDef(
  agents: AgentDef[],
  agentId: string | null,
  agentName: string | null | undefined,
): AgentDef | undefined {
  if (agentId) {
    const byId = agents.find(
      (a) => a.type === agentId || slugify(a.name) === slugify(agentId),
    );
    if (byId) return byId;
  }
  if (agentName) {
    const lower = agentName.toLowerCase();
    const exact = agents.find((a) => a.name.toLowerCase() === lower);
    if (exact) return exact;
    const slugName = slugify(agentName);
    const bySlug = agents.find((a) => a.type === slugName || slugify(a.name) === slugName);
    if (bySlug) return bySlug;
  }
  return undefined;
}

export function findAgentDefByLabel(
  agents: AgentDef[],
  label: string | undefined,
): AgentDef | undefined {
  if (!label?.trim()) return undefined;
  const bySlug = findAgentDef(agents, slugify(label), label);
  if (bySlug) return bySlug;

  const lower = label.toLowerCase();
  const contains = agents.find(
    (a) =>
      lower.includes(a.name.toLowerCase()) ||
      a.name.toLowerCase().includes(lower),
  );
  if (contains) return contains;

  const queryTokens = tokenSet(label);
  if (queryTokens.size === 0) return undefined;

  let best: AgentDef | undefined;
  let bestScore = 0;
  for (const agent of agents) {
    const agentTokens = tokenSet(agent.name);
    let overlap = 0;
    for (const t of queryTokens) {
      if (agentTokens.has(t)) overlap += 1;
    }
    const score = overlap / Math.max(queryTokens.size, agentTokens.size);
    if (score > bestScore && score >= 0.35) {
      bestScore = score;
      best = agent;
    }
  }
  return best;
}

function catalogFromMatch(
  agents: AgentDef[],
  match: CatalogMatch,
): AgentDef | undefined {
  return (
    findAgentDef(agents, match.agent_id, match.name) ??
    findAgentDefByLabel(agents, match.name)
  );
}

export function catalogOutputs(agent: CatalogLike | undefined): string[] {
  if (!agent?.outputs?.length) return [];
  return agent.outputs.filter((s) => s.trim() && s !== "—");
}

export function catalogInputs(agent: CatalogLike | undefined): string[] {
  if (!agent?.inputs?.length) return [];
  return agent.inputs.filter((s) => s.trim() && s !== "—");
}

export function catalogDescription(agent: CatalogLike | undefined): string {
  if (!agent) return "";
  if ("function_summary" in agent && agent.function_summary?.trim()) {
    return agent.function_summary.trim();
  }
  if ("description" in agent && agent.description?.trim()) {
    return agent.description.trim();
  }
  return "";
}

/** Auto-generated pipeline I/O (not from spec.json). */
export function isChainPlaceholderIo(items: string[]): boolean {
  if (!items.length) return true;
  const placeholders = new Set([
    ...GATEWAY_OUTPUTS,
    ...ENTRY_INPUTS,
    ...HUMAN_OUTPUTS,
  ]);
  return items.every(
    (s) =>
      placeholders.has(s) ||
      s.startsWith("Processed result from:") ||
      s.includes(" — structured result for the next step") ||
      s.includes(" — status / metadata for downstream"),
  );
}

/** Use inputs/outputs/function_summary from catalog spec.json for this step. */
export function shouldApplyCatalogSpecIo(
  plan: ArchitecturePlan,
  nodeId: string,
  catalogAgents: AgentDef[],
): boolean {
  const catalog = resolveCatalogAgentForNode(plan, nodeId, catalogAgents);
  if (!catalog) return false;
  const hasCatalogIo =
    catalogInputs(catalog).length > 0 || catalogOutputs(catalog).length > 0;
  if (!hasCatalogIo) return false;

  const node = plan.graph.nodes.find((n) => n.id === nodeId);
  const decision = plan.reuse_decisions.find((d) => d.node_id === nodeId);
  if (decision?.decision === "reuse" || decision?.decision === "adapt") {
    return true;
  }
  if (node?.type === "agent") return true;
  return false;
}

export function catalogSpecIoForNode(
  plan: ArchitecturePlan,
  nodeId: string,
  catalogAgents: AgentDef[],
): { inputs: string[]; outputs: string[]; description: string } {
  const catalog = resolveCatalogAgentForNode(plan, nodeId, catalogAgents);
  return {
    inputs: catalogInputs(catalog),
    outputs: catalogOutputs(catalog),
    description: catalogDescription(catalog),
  };
}

export function resolveCatalogAgentForNode(
  plan: ArchitecturePlan,
  nodeId: string,
  catalogAgents: AgentDef[],
): AgentDef | undefined {
  const node = plan.graph.nodes.find((n) => n.id === nodeId);
  const decision = plan.reuse_decisions.find((d) => d.node_id === nodeId);

  const direct =
    findAgentDef(
      catalogAgents,
      node?.agent_id ?? decision?.agent_id ?? null,
      decision?.agent_name ?? node?.label,
    ) ?? findAgentDefByLabel(catalogAgents, node?.label ?? decision?.node_label);
  if (direct) return direct;

  const labelLower = (node?.label ?? decision?.node_label ?? "").toLowerCase();
  const match = plan.catalog_matches?.find((m) => {
    if (node?.agent_id && m.agent_id === node.agent_id) return true;
    if (decision?.agent_id && m.agent_id === decision.agent_id) return true;
    if (decision?.agent_name && m.name.toLowerCase() === decision.agent_name.toLowerCase()) {
      return true;
    }
    if (labelLower && m.name.toLowerCase() === labelLower) return true;
  });
  if (match) return catalogFromMatch(catalogAgents, match);

  if (decision?.agent_name) {
    return findAgentDefByLabel(catalogAgents, decision.agent_name);
  }
  return undefined;
}

export function getPreviousNodeId(
  flowOrder: string[],
  nodeId: string,
): string | null {
  const idx = flowOrder.indexOf(nodeId);
  if (idx <= 0) return null;
  return flowOrder[idx - 1] ?? null;
}

/** Sensible outputs when catalog is missing or node is gateway/human/build. */
export function inferOutputsForNode(
  node: GraphNode,
  decision: ReuseDecision | undefined,
  catalogAgent: CatalogLike | undefined,
  upstreamInputs: string[],
): string[] {
  const fromCatalog = catalogOutputs(catalogAgent);
  if (fromCatalog.length) return fromCatalog;

  if (node.type === "gateway") return [...GATEWAY_OUTPUTS];
  if (node.type === "human") return [...HUMAN_OUTPUTS];

  if (upstreamInputs.length > 0) {
    return upstreamInputs.map(
      (input) => `Processed result from: ${input}`,
    );
  }

  const label = node.label?.trim() || decision?.node_label?.trim() || "This step";
  return [
    `${label} — structured result for the next step`,
    `${label} — status / metadata for downstream agents`,
  ];
}

/** Full outputs for a node (saved → catalog → inferred). */
export function resolveStepOutputsForNode(
  plan: ArchitecturePlan,
  nodeId: string,
  catalogAgents: AgentDef[],
  flowOrder?: string[],
): string[] {
  const order = flowOrder ?? computeFlowOrder(plan.graph);
  const node = plan.graph.nodes.find((n) => n.id === nodeId);
  if (!node) return [];

  const saved = node.outputs?.filter((s) => s.trim()) ?? [];
  const useCatalogSpec = shouldApplyCatalogSpecIo(plan, nodeId, catalogAgents);
  const catalog = resolveCatalogAgentForNode(plan, nodeId, catalogAgents);
  const fromCatalog = catalogOutputs(catalog);

  if (useCatalogSpec && fromCatalog.length) {
    if (!saved.length || isChainPlaceholderIo(saved)) return fromCatalog;
  }
  if (saved.length) return saved;

  const decision = plan.reuse_decisions.find((d) => d.node_id === nodeId);

  const upstreamInputs = node.inputs?.filter((s) => s.trim()).length
    ? (node.inputs ?? [])
    : deriveStepInputs(plan, nodeId, order, catalogAgents, { skipSaved: true })
        .items;

  return inferOutputsForNode(node, decision, catalog, upstreamInputs);
}

/** Inputs: saved on node, else previous step's outputs (fully resolved). */
export function deriveStepInputs(
  plan: ArchitecturePlan,
  nodeId: string,
  flowOrder: string[],
  catalogAgents: AgentDef[],
  options?: { skipSaved?: boolean },
): { items: string[]; sourceLabel: string | null } {
  const node = plan.graph.nodes.find((n) => n.id === nodeId);
  const saved = node?.inputs?.filter((s) => s.trim()) ?? [];
  const useCatalogSpec = shouldApplyCatalogSpecIo(plan, nodeId, catalogAgents);

  if (useCatalogSpec) {
    const catalog = resolveCatalogAgentForNode(plan, nodeId, catalogAgents);
    const fromCatalog = catalogInputs(catalog);
    if (fromCatalog.length) {
      const prevId = getPreviousNodeId(flowOrder, nodeId);
      const prevNode = prevId
        ? plan.graph.nodes.find((n) => n.id === prevId)
        : undefined;
      const prevLabel =
        prevNode?.label ??
        plan.reuse_decisions.find((d) => d.node_id === prevId)?.node_label ??
        null;
      return {
        items: fromCatalog,
        sourceLabel: prevLabel,
      };
    }
  }

  if (!options?.skipSaved && saved.length && !(useCatalogSpec && isChainPlaceholderIo(saved))) {
    return { items: saved, sourceLabel: null };
  }

  const prevId = getPreviousNodeId(flowOrder, nodeId);
  if (!prevId) {
    const catalog = resolveCatalogAgentForNode(plan, nodeId, catalogAgents);
    const entry = catalogInputs(catalog);
    return {
      items: entry.length ? entry : [...ENTRY_INPUTS],
      sourceLabel: null,
    };
  }

  const prevNode = plan.graph.nodes.find((n) => n.id === prevId);
  const prevLabel =
    prevNode?.label ??
    plan.reuse_decisions.find((d) => d.node_id === prevId)?.node_label ??
    "Previous step";

  const prevOutputs = resolveStepOutputsForNode(
    plan,
    prevId,
    catalogAgents,
    flowOrder,
  );

  return {
    items: prevOutputs.length ? prevOutputs : [...ENTRY_INPUTS],
    sourceLabel: prevLabel,
  };
}

export function deriveStepDescription(
  node: GraphNode | undefined,
  catalogAgent: CatalogLike | undefined,
  decision?: ReuseDecision,
): string {
  if (node?.description?.trim()) return node.description.trim();
  const fromCatalog = catalogDescription(catalogAgent);
  if (fromCatalog) return fromCatalog;
  if (decision?.rationale?.trim()) return decision.rationale.trim();
  return "";
}

export interface StepDetailView {
  inputs: string[];
  outputs: string[];
  description: string;
  inputsFromPrevious: string | null;
  inputsFromCatalog: boolean;
  outputsFromCatalog: boolean;
  outputsInferred: boolean;
  descriptionFromCatalog: boolean;
}

export function buildStepDetailView(
  plan: ArchitecturePlan,
  nodeId: string,
  catalogAgents: AgentDef[],
  flowOrder?: string[],
): StepDetailView {
  const order = flowOrder ?? computeFlowOrder(plan.graph);
  const node = plan.graph.nodes.find((n) => n.id === nodeId);
  const decision = plan.reuse_decisions.find((d) => d.node_id === nodeId);
  const catalog = resolveCatalogAgentForNode(plan, nodeId, catalogAgents);

  const { items: inputs, sourceLabel } = deriveStepInputs(
    plan,
    nodeId,
    order,
    catalogAgents,
  );
  const outputs = resolveStepOutputsForNode(plan, nodeId, catalogAgents, order);
  const description = deriveStepDescription(node, catalog, decision);
  const useCatalogSpec = shouldApplyCatalogSpecIo(plan, nodeId, catalogAgents);
  const catalogIn = catalogInputs(catalog);
  const catalogOut = catalogOutputs(catalog);
  const savedOut = node?.outputs?.filter((s) => s.trim()) ?? [];
  const savedIn = node?.inputs?.filter((s) => s.trim()) ?? [];

  return {
    inputs,
    outputs,
    description,
    inputsFromCatalog:
      useCatalogSpec && catalogIn.length > 0 && (!savedIn.length || isChainPlaceholderIo(savedIn)),
    inputsFromPrevious:
      useCatalogSpec && catalogIn.length > 0 ? sourceLabel : node?.inputs?.length ? null : sourceLabel,
    outputsFromCatalog:
      useCatalogSpec && catalogOut.length > 0 && (!savedOut.length || isChainPlaceholderIo(savedOut)),
    outputsInferred:
      !useCatalogSpec && !savedOut.length && catalogOut.length === 0 && outputs.length > 0,
    descriptionFromCatalog:
      !node?.description?.trim() && catalogDescription(catalog).length > 0,
  };
}

/** Two-pass: outputs first (so chain works), then inputs from upstream. */
export function hydratePlanStepMetadata(
  plan: ArchitecturePlan,
  catalogAgents: AgentDef[],
): ArchitecturePlan {
  if (!plan.graph.nodes.length) return plan;

  const flowOrder = computeFlowOrder(plan.graph);
  let next = plan;

  for (const nodeId of flowOrder) {
    const node = next.graph.nodes.find((n) => n.id === nodeId);
    if (!node) continue;

    if (shouldApplyCatalogSpecIo(next, nodeId, catalogAgents)) {
      const spec = catalogSpecIoForNode(next, nodeId, catalogAgents);
      const patch: {
        inputs?: string[];
        outputs?: string[];
        description?: string;
      } = {};
      if (spec.inputs.length) patch.inputs = spec.inputs;
      if (spec.outputs.length) patch.outputs = spec.outputs;
      if (!node.description?.trim() && spec.description) {
        patch.description = spec.description;
      }
      if (Object.keys(patch).length > 0) {
        next = updatePlanStep(next, nodeId, patch);
      }
      continue;
    }

    const patch: {
      inputs?: string[];
      outputs?: string[];
      description?: string;
    } = {};

    const savedOut = node.outputs?.filter((s) => s.trim()) ?? [];
    if (!savedOut.length || isChainPlaceholderIo(savedOut)) {
      const outputs = resolveStepOutputsForNode(next, nodeId, catalogAgents, flowOrder);
      if (outputs.length) patch.outputs = outputs;
    }

    if (Object.keys(patch).length > 0) {
      next = updatePlanStep(next, nodeId, patch);
    }
  }

  for (const nodeId of flowOrder) {
    const node = next.graph.nodes.find((n) => n.id === nodeId);
    if (!node) continue;
    if (shouldApplyCatalogSpecIo(next, nodeId, catalogAgents)) continue;

    const catalog = resolveCatalogAgentForNode(next, nodeId, catalogAgents);
    const decision = next.reuse_decisions.find((d) => d.node_id === nodeId);

    const patch: {
      inputs?: string[];
      outputs?: string[];
      description?: string;
    } = {};

    const savedIn = node.inputs?.filter((s) => s.trim()) ?? [];
    if (!savedIn.length || isChainPlaceholderIo(savedIn)) {
      patch.inputs = deriveStepInputs(next, nodeId, flowOrder, catalogAgents).items;
    }
    if (!node.description?.trim()) {
      const derived = deriveStepDescription(node, catalog, decision);
      if (derived) patch.description = derived;
    }

    if (Object.keys(patch).length > 0) {
      next = updatePlanStep(next, nodeId, patch);
    }
  }

  return next;
}

export function buildNodeIoMap(
  plan: ArchitecturePlan,
  catalogAgents: AgentDef[],
): Record<string, { inputs: string[]; outputs: string[] }> {
  const flowOrder = computeFlowOrder(plan.graph);
  const map: Record<string, { inputs: string[]; outputs: string[] }> = {};
  for (const nodeId of flowOrder) {
    map[nodeId] = {
      inputs: deriveStepInputs(plan, nodeId, flowOrder, catalogAgents).items,
      outputs: resolveStepOutputsForNode(plan, nodeId, catalogAgents, flowOrder),
    };
  }
  return map;
}
