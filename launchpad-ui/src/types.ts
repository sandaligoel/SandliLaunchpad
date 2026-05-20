/** Mirrors agent_catalog/schemas/architecture_spec.py */

export type FieldStatus = "pending" | "known";
export type SpecStatus = "draft" | "ready";

export const FIELD_GROUPS = {
  requirements: {
    title: "Requirements",
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
    title: "Architectural flow",
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

export interface SpecField {
  key: string;
  label: string;
  value: string | null;
  status: FieldStatus;
  notes?: string | null;
}

export interface ArchitectureSpec {
  status: SpecStatus;
  problem_statement: string;
  fields: Record<string, SpecField>;
  architecture_blueprint?: string | null;
}

export interface ChatMessage {
  role: "assistant" | "user";
  content: string;
  field_key?: string | null;
}

export interface InterviewQuestion {
  field_key: string;
  question: string;
  chips: string[];
}

export interface InterviewSession {
  id: string;
  spec: ArchitectureSpec;
  messages: ChatMessage[];
  pending_question: InterviewQuestion | null;
}

export interface SessionResponse {
  session: InterviewSession;
}
