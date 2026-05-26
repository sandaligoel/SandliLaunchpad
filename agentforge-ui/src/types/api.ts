export type AgentType =
  | "mcp"
  | "retrieval"
  | "text-to-sql"
  | "text-to-sap"
  | "text-to-salesforce"
  | "web-search"
  | "email-gen"
  | "sql-insight"
  | "router"
  | "answer-gen"
  | "query-transformer"
  | "tool"
  | "video-gen"
  | "image-gen"
  | "semantic-search";

export type RunStatus = "success" | "failed" | "running" | "queued";
export type WorkflowStatus = "draft" | "published" | "archived";

export type FieldType =
  | "text"
  | "textarea"
  | "number"
  | "select"
  | "multiselect"
  | "radio"
  | "slider"
  | "file"
  | "tags"
  | "toggle";

export interface FieldDef {
  key: string;
  label: string;
  type: FieldType;
  required?: boolean;
  description?: string;
  placeholder?: string;
  options?: string[];
  min?: number;
  max?: number;
  step?: number;
  default?: unknown;
}

export interface OutputDef {
  name: string;
  description: string;
}

export interface AgentDef {
  type: AgentType;
  name: string;
  category: string;
  description: string;
  summary: string;
  color: string;
  icon: string;
  inputs: string[];
  outputs: string[];
  fields: FieldDef[];
  outputFields: OutputDef[];
  defaultConfig: Record<string, unknown>;
}

export interface WorkflowSummary {
  id: string;
  name: string;
  description: string;
  status: WorkflowStatus;
  agentCount: number;
  lastRun: string;
  successRate: number;
  version: string;
  owner: string;
}

export interface RunStep {
  nodeId: string;
  agent: AgentType;
  label: string;
  status: RunStatus;
  latencyMs: number;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
}

export interface Run {
  id: string;
  workflowId: string;
  workflowName: string;
  status: RunStatus;
  startedAt: string;
  durationMs: number;
  tokens: number;
  cost: number;
  steps: RunStep[];
}

export interface Credential {
  id: string;
  name: string;
  provider: string;
  type: "api_key" | "connection_string" | "oauth";
  masked: string;
  envRef: string;
  createdAt: string;
}

export interface Template {
  id: string;
  name: string;
  description: string;
  agents: AgentType[];
  category: string;
}

export interface DashboardStats {
  totalWorkflows: number;
  activeAgents: number;
  runsToday: number;
  avgLatency: string;
}

export interface RunsOverTimeEntry {
  day: string;
  success: number;
  failed: number;
}

export interface AgentUsageEntry {
  name: string;
  uses: number;
}
