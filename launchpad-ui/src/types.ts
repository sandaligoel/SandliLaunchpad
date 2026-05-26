/** Mirrors agent_catalog/schemas/architecture_spec.py */

export type FieldStatus = "pending" | "known";
export type SpecStatus = "draft" | "sufficient" | "ready";

export const FIELD_GROUPS = {
  requirements: {
    title: "About your idea",
    keys: [
      "use_case",
      "data_volume",
      "accuracy_target",
      "hitl_behavior",
      "integrations",
      "latency_target",
      "model_preference",
      "deployment_platform",
    ] as const,
  },
  architecture: {
    title: "How it should work",
    keys: [
      "architectural_flow",
      "architectural_flow_feedback",
      "architectural_pattern",
      "core_components",
      "data_flow",
      "orchestration_model",
      "scalability_constraints",
    ] as const,
  },
} as const;

export const FIELD_ORDER = [
  ...FIELD_GROUPS.requirements.keys,
  ...FIELD_GROUPS.architecture.keys,
] as const;

export type FieldKey = (typeof FIELD_ORDER)[number];

export type FieldSource = "problem_statement" | "user_answer" | "inferred";

export interface SpecField {
  key: string;
  label: string;
  value: string | null;
  status: FieldStatus;
  notes?: string | null;
  source?: FieldSource | null;
  confidence?: number | null;
}

export interface CatalogHint {
  agent_id: string;
  name: string;
  category: string;
  origin_client: string;
  function_summary: string;
  score: number;
  origin_project?: string;
  integrations?: string;
  model_used?: string;
  status?: string;
}

export interface GraphNode {
  id: string;
  label: string;
  type: "agent" | "custom" | "gateway" | "human";
  agent_id?: string | null;
  description?: string | null;
}

export interface GraphEdge {
  from_id: string;
  to_id: string;
  label?: string | null;
}

export interface GraphDraft {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface ArchitectureSpec {
  status: SpecStatus;
  problem_statement: string;
  fields: Record<string, SpecField>;
  transcript_summary?: string;
  catalog_hints?: CatalogHint[];
  architecture_blueprint?: string | null;
  graph_draft?: GraphDraft | null;
}

export interface ChatMessage {
  role: "assistant" | "user";
  content: string;
  field_key?: string | null;
}

export interface ClarifyingQuestionItem {
  id: string;
  question: string;
  why_it_matters: string;
}

export interface InterviewQuestion {
  field_key: string;
  question: string;
  chips: string[];
  why_it_matters?: string | null;
}

export type ReuseDecisionType = "reuse" | "adapt" | "build";

export interface CatalogMatch {
  agent_id: string;
  name: string;
  category: string;
  origin_client: string;
  origin_project: string;
  function_summary: string;
  score: number;
  matched_for: string;
}

export interface ReuseDecision {
  node_id: string;
  node_label: string;
  decision: ReuseDecisionType;
  agent_id?: string | null;
  agent_name?: string | null;
  rationale: string;
  catalog_score?: number | null;
}

export type ValidationLevel = "pass" | "warn" | "fail";

export interface RemediationOption {
  id: string;
  label: string;
  description?: string;
  finding_id?: string;
  action: string;
  node_id?: string | null;
  decision?: "reuse" | "adapt" | "build" | null;
  agent_id?: string | null;
  agent_name?: string | null;
  catalog_score?: number | null;
  gateway_label?: string | null;
  question_text?: string | null;
}

export interface ValidationResolution {
  action: string;
  action_id: string;
  label?: string;
}

export interface ValidationFinding {
  level: ValidationLevel;
  code: string;
  message: string;
  node_id?: string | null;
  finding_id?: string | null;
  finding_key?: string | null;
  blocks_approval?: boolean;
  help_text?: string;
  remediations?: RemediationOption[];
  resolved?: boolean;
  resolution?: ValidationResolution | null;
}

export interface ArchitectureValidationReport {
  overall: ValidationLevel;
  pass_count: number;
  warn_count: number;
  fail_count: number;
  structural_fail_count?: number;
  unresolved_actionable_count?: number;
  can_approve?: boolean;
  approval_hint?: string;
  items: ValidationFinding[];
  node_status: Record<string, ValidationLevel>;
}

export interface ArchitecturePlan {
  graph: GraphDraft;
  reuse_decisions: ReuseDecision[];
  catalog_matches: CatalogMatch[];
  summary_markdown: string;
  open_questions: string[];
  validation?: ArchitectureValidationReport | null;
  validation_resolutions?: Record<string, ValidationResolution>;
  architecture_approved?: boolean;
}

export interface InterviewSession {
  id: string;
  spec: ArchitectureSpec;
  messages: ChatMessage[];
  pending_question: InterviewQuestion | null;
  last_answered_field?: string | null;
  architecture_plan?: ArchitecturePlan | null;
  clarifying_questions?: ClarifyingQuestionItem[];
  clarifying_answers?: Record<string, string>;
}

export interface SessionResponse {
  session: InterviewSession;
}

export interface ArchitectureResponse {
  session_id: string;
  plan: ArchitecturePlan;
}
