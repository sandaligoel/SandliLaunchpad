import type { AgentDef, FieldDef } from "@/types/api";

const API_BASE = import.meta.env.VITE_AFFINE_API_BASE ?? "";

export interface CatalogAgentRecord {
  id: string;
  name: string;
  version: string;
  category: string;
  function_summary: string;
  inputs: string[];
  outputs: string[];
  model_used: string;
  tech_stack: string[];
  integrations: string[];
  origin_project: string;
  origin_client: string;
  vertical: string;
  status: string;
  typical_accuracy?: string | null;
  notes?: string | null;
}

export interface CatalogAgentsResponse {
  agents: CatalogAgentRecord[];
  count: number;
}

const CATEGORY_STYLE: Record<
  string,
  { color: string; icon: AgentDef["icon"] }
> = {
  "Document & Data": { color: "#2E86C1", icon: "Database" },
  "Quality & Compliance": { color: "#5B5EA6", icon: "Building" },
  "Finance & Procurement": { color: "#16A085", icon: "BarChart3" },
  "Supply Chain & Logistics": { color: "#E67E22", icon: "GitBranch" },
  "Sales & Revenue": { color: "#E74C3C", icon: "Mail" },
  "Healthcare & Compliance": { color: "#1ABC9C", icon: "Building" },
};

function metaFields(agent: CatalogAgentRecord): FieldDef[] {
  const rows: Array<{ key: string; label: string; value: string }> = [
    { key: "client", label: "Client", value: agent.origin_client },
    { key: "project", label: "Project", value: agent.origin_project },
    { key: "vertical", label: "Vertical", value: agent.vertical },
    { key: "model", label: "Model", value: agent.model_used },
    { key: "status", label: "Status", value: agent.status },
    { key: "version", label: "Version", value: agent.version },
  ];
  if (agent.integrations.length) {
    rows.push({
      key: "integrations",
      label: "Integrations",
      value: agent.integrations.join(", "),
    });
  }
  if (agent.tech_stack.length) {
    rows.push({
      key: "tech",
      label: "Tech stack",
      value: agent.tech_stack.join(", "),
    });
  }
  if (agent.typical_accuracy) {
    rows.push({
      key: "accuracy",
      label: "Typical accuracy",
      value: agent.typical_accuracy,
    });
  }
  return rows
    .filter((r) => r.value?.trim())
    .map((r) => ({
      key: r.key,
      label: r.label,
      type: "text" as const,
      description: r.value,
      default: r.value,
    }));
}

/** Map spec.json agent to Agent Library card shape (same UI as mock registry). */
export function catalogAgentToAgentDef(agent: CatalogAgentRecord): AgentDef {
  const style = CATEGORY_STYLE[agent.category] ?? {
    color: "#1B5E8C",
    icon: "Wrench" as const,
  };
  const summaryParts = [agent.origin_client, agent.origin_project].filter(
    Boolean,
  );
  return {
    type: agent.id,
    name: agent.name,
    category: agent.category,
    description: agent.function_summary,
    summary:
      summaryParts.join(" · ") ||
      agent.notes?.slice(0, 120) ||
      "Affine built agent from catalog",
    color: style.color,
    icon: style.icon,
    inputs: agent.inputs.length ? agent.inputs : ["—"],
    outputs: agent.outputs.length ? agent.outputs : ["—"],
    fields: metaFields(agent),
    outputFields: [],
    defaultConfig: {},
  };
}

export async function fetchCatalogAgents(): Promise<AgentDef[]> {
  const res = await fetch(`${API_BASE}/api/catalog/agents`);
  if (!res.ok) {
    throw new Error(`Catalog API failed (${res.status})`);
  }
  const data = (await res.json()) as CatalogAgentsResponse;
  return data.agents.map(catalogAgentToAgentDef);
}
