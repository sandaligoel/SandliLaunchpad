/** Mirrors backend/schemas — used by Launchpad interview (AFFINE API). */

export type FieldStatus = "pending" | "known";
export type SpecStatus = "draft" | "sufficient" | "ready";

/** All requirement slots (display + backend spec). */
export const REQUIREMENTS_FIELD_KEYS = [
  "use_case",
  "data_volume",
  "accuracy_target",
  "hitl_behavior",
  "integrations",
  "latency_target",
  "model_preference",
  "deployment_platform",
] as const;

/** All architecture slots (display + backend spec). */
export const ARCHITECTURE_FIELD_KEYS = [
  "architectural_flow",
  "architectural_flow_feedback",
  "architectural_pattern",
  "core_components",
  "data_flow",
  "orchestration_model",
  "scalability_constraints",
] as const;

/** Fields the chat asks (matches backend USER_INTERVIEW_FIELD_KEYS). */
export const USER_INTERVIEW_REQUIREMENT_KEYS = [
  "hitl_behavior",
  "integrations",
] as const;

export const USER_INTERVIEW_ARCHITECTURE_KEYS = [
  "architectural_flow",
  "data_flow",
  "core_components",
  "orchestration_model",
] as const;

export const USER_INTERVIEW_FIELD_KEYS = [
  ...USER_INTERVIEW_REQUIREMENT_KEYS,
  ...USER_INTERVIEW_ARCHITECTURE_KEYS,
] as const;

/** Plain labels for the topic shown above each interview question. */
export const INTERVIEW_TOPIC_LABELS: Record<string, string> = {
  hitl_behavior: "When someone should review results",
  integrations: "Where data comes from and goes",
  architectural_flow: "Order of steps in your process",
  data_flow: "Where information moves between steps",
  core_components: "Main parts you need",
  orchestration_model: "How steps run (automatic, parallel, or manual)",
};

export const FIELD_GROUPS = {
  requirements: {
    title: "Requirements",
    keys: REQUIREMENTS_FIELD_KEYS,
  },
  architecture: {
    title: "Architectural requirements",
    keys: ARCHITECTURE_FIELD_KEYS,
  },
} as const;

export const FIELD_ORDER = [
  ...REQUIREMENTS_FIELD_KEYS,
  ...ARCHITECTURE_FIELD_KEYS,
] as const;

export type FieldKey = (typeof FIELD_ORDER)[number];

export function isUserInterviewFieldKey(key: string): boolean {
  return (USER_INTERVIEW_FIELD_KEYS as readonly string[]).includes(key);
}

export function isClarifyingFieldKey(key: string | null | undefined): boolean {
  return Boolean(key?.startsWith("clarifying:"));
}

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
  inputs?: string[];
  outputs?: string[];
  /** User-edited input payload shown in Step Details (JSON object). */
  input_json?: Record<string, unknown> | null;
  /** User-edited output payload shown in Step Details (JSON object). */
  output_json?: Record<string, unknown> | null;
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
  topic_label?: string | null;
  question: string;
  chips: string[];
  why_it_matters?: string | null;
  /** Closest catalog-backed option (usually first chip). */
  suggested_chip?: string | null;
  catalog_reference?: string | null;
  suggestion_reason?: string | null;
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

export interface AgentWorkflowState {
  current_phase?: "start" | "interview" | "completion_check" | "handover";
  query_understood: string;
  matched_agents: { agent_id: string; name: string; reason: string }[];
  questions: {
    field_key: string;
    agent_id: string;
    agent_name: string;
    input_name: string;
    question: string;
    chips: string[];
    cluster?: string;
    impact_score?: number;
    dependency_score?: number;
    uncertainty_score?: number;
    business_criticality_score?: number;
    rank_score?: number;
  }[];
  answers: Record<string, string>;
  next_index: number;
  question_count?: number;
  question_budget?: number;
  hard_cap?: number;
  coverage_score?: number;
  risk_score?: number;
  required_input_count?: number;
  critical_items?: string[];
  completion_reason?: string | null;
  current_cluster?: string | null;
}

export interface InterviewSession {
  id: string;
  spec: ArchitectureSpec;
  messages: ChatMessage[];
  pending_question: InterviewQuestion | null;
  last_answered_field?: string | null;
  architecture_plan?: ArchitecturePlan | null;
  clarifying_questions?: ClarifyingQuestionItem[];
  agent_workflow?: AgentWorkflowState | null;
  clarifying_answers?: Record<string, string>;
}

export interface SessionResponse {
  session: InterviewSession;
}

export interface ArchitectureResponse {
  session_id: string;
  plan: ArchitecturePlan;
}
