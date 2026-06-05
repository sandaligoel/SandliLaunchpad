import type { StepComponentKind } from "@/utils/stepComponentKind";

export type ReuseDecision = "reuse" | "adapt" | "build";

export type GraphNodeType =
  | "agent"
  | "tool"
  | "data_store"
  | "human"
  | "api"
  | "orchestrator"
  | "custom"
  | "gateway";

export type GraphEdgeType =
  | "uses"
  | "produces"
  | "invokes"
  | "reads_from"
  | "escalates_to"
  | "part_of";

export interface GraphNode {
  id: string;
  type: GraphNodeType;
  label: string;
  description?: string;
  layer?: number;
  catalog_agent_id?: string;
  source_project?: string;
  reuse_decision?: ReuseDecision;
  metadata?: Record<string, string>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type?: GraphEdgeType;
  label?: string;
}

export interface CapabilityMatch {
  capability: string;
  decision: ReuseDecision;
  catalog_agent_name?: string;
  catalog_project?: string;
  search_score?: number;
  rationale?: string;
}

export interface PlanReuseDecision {
  node_id: string;
  node_label?: string;
  decision: ReuseDecision;
  agent_id?: string;
  agent_name?: string;
  catalog_score?: number;
  rationale?: string;
}

export interface ArchitecturePlan {
  session_id?: string;
  spec_summary?: Record<string, string>;
  capabilities?: CapabilityMatch[];
  nodes: GraphNode[];
  edges: GraphEdge[];
  reuse_decisions?: PlanReuseDecision[];
  catalog_matches?: Array<{
    agent_id: string;
    name: string;
    score?: number;
    matched_for?: string;
    function_summary?: string;
    origin_project?: string;
  }>;
  reuse_count?: number;
  build_count?: number;
  narrative?: string;
}

export type FlowLane =
  | "input"
  | "orchestration"
  | "execution"
  | "merge"
  | "hitl";

export type FlowNodeKind =
  | "input"
  | "orchestrator"
  | "agent-reuse"
  | "agent-adapt"
  | "agent-build"
  | "merge"
  | "decision"
  | "human"
  | "lane-label"
  | "lane-band"
  | "parallel-group";

export type ExecutionStatus = "idle" | "running" | "success" | "failed" | "skipped";

export interface NodeRuntimeMeta {
  status: ExecutionStatus;
  latencyMs: number;
  retries: number;
  tools: string[];
  inputs: string[];
  outputs: string[];
  inputJson?: Record<string, unknown>;
  outputJson?: Record<string, unknown>;
  catalog?: string;
  project?: string;
}

export interface FlowNodeData extends Record<string, unknown> {
  kind: FlowNodeKind;
  label: string;
  description?: string;
  lane: FlowLane;
  reuse?: ReuseDecision;
  /** Agent (catalog), Tool (API/data), or Function (orchestration/HITL/custom). */
  componentKind?: StepComponentKind;
  catalogAgentName?: string;
  runtime: NodeRuntimeMeta;
  expanded?: boolean;
  pipelineOrder?: number;
  isActive?: boolean;
  isDimmed?: boolean;
  isHighlighted?: boolean;
  branchLabel?: string;
  capabilityId?: string;
  measuredWidth?: number;
  measuredHeight?: number;
}

export interface FlowEdgeData extends Record<string, unknown> {
  edgeKind: "sequential" | "parallel" | "merge" | "retry" | "data";
  label?: string;
  animated?: boolean;
  isActive?: boolean;
  isFlowing?: boolean;
}
