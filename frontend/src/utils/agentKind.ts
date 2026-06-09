import type { CatalogAgentRecord } from "@/api/affine/catalog";
import type { AgentDef } from "@/types/api";

export type ImplementationKind = "agent" | "function" | "tool";

export type KindTone = "canvas" | "sidebar";

export type KindMeta = {
  label: string;
  shortLabel: string;
  /** Text on dark canvas nodes */
  color: string;
  solid: string;
  bg: string;
  border: string;
  glow: string;
  stripe: string;
  nodeBg: string;
  rowBg: string;
  /** Readable text on light sidebar / library cards */
  lightText: string;
  lightBg: string;
  lightBorder: string;
};

export function kindBadgeStyle(
  kind: ImplementationKind,
  tone: KindTone = "canvas",
): { color: string; background: string; borderColor: string; boxShadow?: string } {
  const meta = KIND_META[kind];
  if (tone === "sidebar") {
    return {
      color: meta.lightText,
      background: meta.lightBg,
      borderColor: meta.lightBorder,
    };
  }
  return {
    color: meta.color,
    background: meta.bg,
    borderColor: meta.border,
    boxShadow: `0 0 14px ${meta.glow}`,
  };
}

export const KIND_META: Record<ImplementationKind, KindMeta> = {
  agent: {
    label: "Agent",
    shortLabel: "AGENT",
    color: "#ddd6fe",
    solid: "#8b5cf6",
    bg: "rgba(139,92,246,0.32)",
    border: "rgba(167,139,250,0.95)",
    glow: "rgba(139,92,246,0.55)",
    stripe: "#7c3aed",
    nodeBg:
      "linear-gradient(145deg, rgba(91,33,182,0.42) 0%, rgba(15,23,42,0.94) 58%)",
    rowBg: "rgba(139,92,246,0.12)",
    lightText: "#5b21b6",
    lightBg: "#ede9fe",
    lightBorder: "#a78bfa",
  },
  function: {
    label: "Function",
    shortLabel: "FUNCTION",
    color: "#fde68a",
    solid: "#f59e0b",
    bg: "rgba(245,158,11,0.32)",
    border: "rgba(251,191,36,0.95)",
    glow: "rgba(245,158,11,0.5)",
    stripe: "#d97706",
    nodeBg:
      "linear-gradient(145deg, rgba(180,83,9,0.38) 0%, rgba(15,23,42,0.94) 58%)",
    rowBg: "rgba(245,158,11,0.12)",
    lightText: "#92400e",
    lightBg: "#fef3c7",
    lightBorder: "#fbbf24",
  },
  tool: {
    label: "Tool",
    shortLabel: "TOOL",
    color: "#a5f3fc",
    solid: "#06b6d4",
    bg: "rgba(6,182,212,0.32)",
    border: "rgba(34,211,238,0.95)",
    glow: "rgba(6,182,212,0.5)",
    stripe: "#0891b2",
    nodeBg:
      "linear-gradient(145deg, rgba(8,145,178,0.38) 0%, rgba(15,23,42,0.94) 58%)",
    rowBg: "rgba(6,182,212,0.12)",
    lightText: "#0e7490",
    lightBg: "#cffafe",
    lightBorder: "#22d3ee",
  },
};

function classifyFromBlob(blob: string, techBlob: string, name: string): ImplementationKind {
  const lower = blob.toLowerCase();
  const tech = techBlob.toLowerCase();
  const n = name.toLowerCase();

  if (lower.includes("agents:") || n.includes("agent chain") || tech.includes("autogen")) {
    return "agent";
  }
  if (tech.includes("llm_functions") || lower.includes("llm_functions")) {
    return "function";
  }
  if (
    ["count_function", "generic_function", "final_answer_function", "daily_kpi"].some(
      (t) => lower.includes(t),
    )
  ) {
    return "function";
  }
  if (
    (n.includes(" agent") || n.endsWith(" agent") || n.includes(" chain")) &&
    !tech.includes("llm_functions")
  ) {
    return "agent";
  }

  const toolMarkers = [
    "roboflow",
    "detect_crop.py",
    "yolo",
    "catboost",
    "scikit-learn",
    "sklearn",
    "images/edits",
    "videos api",
    "azure-search-documents",
    "semantic.py",
    "competitive_scoring.py",
    "not a trained ml model",
    "sql_tool",
  ];
  if (toolMarkers.some((m) => lower.includes(m))) return "tool";
  if (tech.includes("python-docx") && !tech.includes("azure openai")) return "tool";

  if (
    ["embedder", "vector retrieval", "semantic search", "row detector", "product detector", "simulator", "stub", "analysis engine"].some(
      (p) => n.includes(p),
    )
  ) {
    return "tool";
  }

  if (tech.includes("azure openai") || lower.includes("graphrag") || tech.includes("google-genai")) {
    return "agent";
  }
  if (tech.includes("python") && !tech.includes("openai") && !tech.includes("genai")) {
    return "tool";
  }
  return "agent";
}

export function classifyCatalogAgent(agent: CatalogAgentRecord): ImplementationKind {
  if (agent.implementation_kind) {
    return agent.implementation_kind;
  }
  const blob = `${agent.notes ?? ""} ${agent.tech_stack.join(" ")} ${agent.name} ${agent.function_summary}`;
  return classifyFromBlob(blob, agent.tech_stack.join(" "), agent.name);
}

export function classifyAgentDef(agent: AgentDef): ImplementationKind {
  if (agent.implementationKind) {
    return agent.implementationKind;
  }
  const fields = agent.fields ?? [];
  const notes = fields.find((f) => f.key === "notes")?.description ?? "";
  const tech = fields.find((f) => f.key === "tech")?.description ?? "";
  const blob = `${notes} ${tech} ${agent.name} ${agent.description}`;
  return classifyFromBlob(blob, tech, agent.name);
}

/** Infer agent / function / tool for build-new or gateway steps without catalog id. */
export function inferNodeImplementationKind(
  label: string,
  description?: string,
  nodeType?: string,
): ImplementationKind | undefined {
  const blob = `${label} ${description ?? ""}`.toLowerCase();
  if (nodeType === "human" || /\b(hitl|analyst review|human gate)\b/.test(blob)) {
    return undefined;
  }
  if (/\b(gateway|intake|entrypoint|entry point)\b/.test(blob)) return "tool";
  if (/\b(blob storage|data store|azure blob|s3|persist|storage)\b/.test(blob)) {
    return "tool";
  }
  return classifyFromBlob(blob, "", label);
}

export function parseSubcomponents(notes?: string | null): string[] {
  if (!notes) return [];
  const match = notes.match(/agents:\s*([^.;]+)/i);
  if (!match) return [];
  return match[1]
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}
