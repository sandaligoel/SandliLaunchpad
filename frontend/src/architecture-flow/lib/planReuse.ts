import type { ArchitecturePlan, GraphNode, PlanReuseDecision, ReuseDecision } from "@/architecture-flow/types/plan";

function norm(s: string): string {
  return s.trim().toLowerCase().replace(/\s+/g, " ");
}

/** Match reuse row to graph node when ids differ after planning/sanitize. */
export function findReuseDecisionForNode(
  plan: ArchitecturePlan | null | undefined,
  node: GraphNode
): PlanReuseDecision | undefined {
  const list = plan?.reuse_decisions;
  if (!list?.length) return undefined;

  const byId = list.find((d) => d.node_id === node.id);
  if (byId) return byId;

  const label = norm(node.label || "");
  if (label) {
    const byLabel = list.find((d) => norm(d.node_label || "") === label);
    if (byLabel) return byLabel;
  }

  const slug = label.replace(/[^a-z0-9]+/g, "-");
  if (slug) {
    return list.find((d) => norm(d.node_id || "").replace(/_/g, "-") === slug);
  }

  return undefined;
}

export function getNodeReuseDecision(
  plan: ArchitecturePlan | null | undefined,
  node: GraphNode
): ReuseDecision {
  const onNode = node.reuse_decision;
  if (onNode === "reuse" || onNode === "adapt" || onNode === "build") return onNode;

  const fromPlan = findReuseDecisionForNode(plan, node);
  if (fromPlan?.decision) return fromPlan.decision;

  return "build";
}

/** Catalog match score (0–1) for a step, from reuse decisions or capability search. */
export function resolveCatalogConfidence(
  plan: ArchitecturePlan | null | undefined,
  node: GraphNode
): number | null {
  if (!plan || !node) return null;

  const dec = findReuseDecisionForNode(plan, node);
  if (dec?.catalog_score != null) {
    const s = Number(dec.catalog_score);
    if (!Number.isNaN(s) && s > 0) return s <= 1 ? s : s / 100;
  }

  const capKey = node.metadata?.capability;
  if (capKey && plan.capabilities?.length) {
    const cap = plan.capabilities.find(
      (c) =>
        c.capability === capKey ||
        c.capability === String(capKey).replace(/_/g, "-")
    );
    if (cap?.search_score != null && cap.search_score > 0) return cap.search_score;
  }

  const label = (node.label || "").toLowerCase();
  for (const m of plan.catalog_matches || []) {
    const score = typeof m.score === "number" ? m.score : null;
    if (score == null || score <= 0) continue;
    const mf = (m.matched_for || m.name || "").toLowerCase();
    if (!mf) continue;
    if (capKey && (mf === capKey || mf.replace(/\s+/g, "-") === capKey)) return score;
    if (label && (label.includes(mf.slice(0, 14)) || mf.includes(label.slice(0, 14)))) {
      return score;
    }
  }

  return null;
}

/** Steps that appear in the builder palette and walkthrough metrics. */
export function isWorkflowStepNode(n: GraphNode): boolean {
  return (
    n.type === "agent" ||
    n.type === "custom" ||
    n.type === "gateway" ||
    n.type === "api" ||
    n.type === "human"
  );
}

export type WorkflowStepStats = {
  /** All workflow steps in the plan (agents, gateways, human gates, etc.). */
  steps: number;
  reuse: number;
  adapt: number;
  build: number;
  /** Steps mapped to catalog agents (reuse + adapt). */
  catalog: number;
  /** @deprecated Use `steps` — kept for older call sites. */
  agents: number;
};

export function countReuseStats(plan: ArchitecturePlan | null): WorkflowStepStats {
  if (!plan?.nodes?.length) {
    return { steps: 0, reuse: 0, adapt: 0, build: 0, catalog: 0, agents: 0 };
  }
  const stepNodes = plan.nodes.filter(isWorkflowStepNode);
  let reuse = 0;
  let adapt = 0;
  let build = 0;
  for (const step of stepNodes) {
    const d = getNodeReuseDecision(plan, step);
    if (d === "reuse") reuse++;
    else if (d === "adapt") adapt++;
    else build++;
  }
  const steps = stepNodes.length;
  return {
    steps,
    agents: steps,
    reuse,
    adapt,
    build,
    catalog: reuse + adapt,
  };
}
