import type { GraphNode, ReuseDecision } from "@/architecture-flow/types/plan";

/** How this workflow step is classified in the architecture. */
export type StepComponentKind = "agent" | "tool" | "function";

const KIND_LABELS: Record<StepComponentKind, string> = {
  agent: "Agent",
  tool: "Tool",
  function: "Function",
};

const KIND_HINTS: Record<StepComponentKind, string> = {
  agent: "Catalog agent from spec.json (reusable capability)",
  tool: "Integration, API, or data interface",
  function: "Orchestration step or custom workflow function",
};

export function stepComponentKindLabel(kind: StepComponentKind): string {
  return KIND_LABELS[kind];
}

export function stepComponentKindHint(kind: StepComponentKind): string {
  return KIND_HINTS[kind];
}

/**
 * Classify a canvas step for the inspector.
 * Agent = catalog-backed step; Tool = gateways/APIs/data; Function = custom/orchestration/HITL.
 */
export function resolveStepComponentKind(
  node: GraphNode | undefined,
  reuse: ReuseDecision,
): StepComponentKind {
  if (!node) {
    return reuse === "reuse" || reuse === "adapt" ? "agent" : "function";
  }

  if (node.type === "orchestrator" || node.type === "human") {
    return "function";
  }

  // Catalog-backed steps stay Agent even when the planner typed them api/gateway.
  if (
    node.type === "agent" ||
    node.catalog_agent_id ||
    reuse === "reuse" ||
    reuse === "adapt"
  ) {
    return "agent";
  }

  if (node.type === "tool" || node.type === "api" || node.type === "data_store") {
    return "tool";
  }

  const text = `${node.label} ${node.description || ""}`.toLowerCase();
  if (
    text.includes("gateway") ||
    text.includes("upload") ||
    text.includes("ingest") ||
    text.includes(" blob") ||
    text.includes("api endpoint") ||
    text.includes("webhook")
  ) {
    return "tool";
  }

  return "function";
}
