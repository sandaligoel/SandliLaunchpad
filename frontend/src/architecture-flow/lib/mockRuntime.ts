import type { ArchitecturePlan, GraphNode, NodeRuntimeMeta } from "@/architecture-flow/types/plan";
import { parseSubcomponents } from "@/utils/agentKind";

const TOOL_POOL = [
  "Azure AI Search",
  "Document Intelligence",
  "Vision API",
  "Rules engine",
  "SP-API",
];

function hash(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h << 5) - h + s.charCodeAt(i);
  return Math.abs(h);
}

function upstreamLabels(plan: ArchitecturePlan | undefined, nodeId: string): string[] {
  if (!plan?.edges?.length) return [];
  return plan.edges
    .filter((e) => e.target === nodeId)
    .map((e) => plan.nodes.find((n) => n.id === e.source)?.label || e.source)
    .filter(Boolean);
}

function parseMetaJsonObject(
  raw: string | undefined,
): Record<string, unknown> | undefined {
  if (!raw?.trim()) return undefined;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }
  } catch {
    /* ignore */
  }
  return undefined;
}

function applySavedJsonOverrides(
  meta: Record<string, string>,
  built: { inputJson: Record<string, unknown>; outputJson: Record<string, unknown> },
): { inputJson: Record<string, unknown>; outputJson: Record<string, unknown> } {
  const customIn = parseMetaJsonObject(meta.input_json);
  const customOut = parseMetaJsonObject(meta.output_json);
  return {
    inputJson: customIn ?? built.inputJson,
    outputJson: customOut ?? built.outputJson,
  };
}

function catalogListsFromMeta(meta: Record<string, string>): {
  inputs: string[];
  outputs: string[];
} {
  const parse = (raw: string | undefined): string[] => {
    if (!raw) return [];
    try {
      const parsed = JSON.parse(raw) as unknown;
      if (Array.isArray(parsed)) {
        return parsed.filter((x): x is string => typeof x === "string" && x.trim());
      }
    } catch {
      /* ignore */
    }
    return [];
  };
  return {
    inputs: parse(meta.catalog_inputs),
    outputs: parse(meta.catalog_outputs),
  };
}

/** Build display payloads for Step Details / node inspector (from plan graph). */
export function buildNodeIoPayload(
  node: GraphNode,
  plan?: ArchitecturePlan
): { inputJson: Record<string, unknown>; outputJson: Record<string, unknown> } {
  const label = (node.label || node.id || "step").toLowerCase();
  const upstream = upstreamLabels(plan, node.id);
  const meta = node.metadata || {};
  const capability = meta.capability || node.id;
  const catalogLists = catalogListsFromMeta(meta);

  if (
    node.type === "agent" ||
    node.type === "custom" ||
    node.type === "tool"
  ) {
    if (catalogLists.inputs.length || catalogLists.outputs.length) {
      const capability = (node.label || node.id || "step")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "");
      const payload: Record<string, unknown> = {};
      catalogLists.inputs.forEach((item, i) => {
        payload[`field_${i + 1}`] = item;
      });
      const result: Record<string, unknown> = {};
      catalogLists.outputs.forEach((item, i) => {
        result[`field_${i + 1}`] = item;
      });
      return {
        inputJson: {
          capability,
          upstream: upstream.length ? upstream : [],
          payload: Object.keys(payload).length ? payload : {},
        },
        outputJson: {
          status: "success",
          capability,
          result: Object.keys(result).length ? result : {},
        },
      };
    }
  }

  if (node.type === "data_store" || node.type === "api") {
    return {
      inputJson: {
        source: "external",
        assets: ["reference_photos", "sku_metadata", "brand_guidelines.pdf"],
        problem_statement: plan?.spec_summary?.use_case || plan?.spec_summary?.problem_statement,
      },
      outputJson: {
        normalized_assets: ["image_ref_001.png", "sku_8842.json"],
        routing_hint: "orchestrator",
      },
    };
  }

  if (node.type === "orchestrator") {
    return {
      inputJson: {
        workflow_request: {
          assets: upstream.length ? upstream : ["normalized_assets"],
          policy_pack: "guardrails.pdf",
        },
      },
      outputJson: {
        execution_plan: {
          steps: (plan?.nodes || [])
            .filter((n) => n.type === "agent")
            .map((n) => ({ id: n.id, label: n.label, reuse: n.reuse_decision })),
        },
      },
    };
  }

  if (node.type === "human") {
    return {
      inputJson: {
        review_package: {
          from_upstream: upstream,
          violations_summary: "2 blocking, 1 warning",
        },
      },
      outputJson: {
        decision: "approve_with_edits",
        reviewer_notes: "",
        approved_assets: [],
      },
    };
  }

  const baseIn: Record<string, unknown> = {
    capability,
    upstream: upstream.length ? upstream : ["workflow_payload"],
    payload: meta.input_example || {
      images: ["generated_main.png", "generated_infographic.png"],
      metadata: { sku: "SKU-8842", marketplace: "amazon" },
    },
  };

  let baseOut: Record<string, unknown> = {
    status: "success",
    capability,
    result: meta.output_example || { structured_fields: {} },
  };

  if (label.includes("generat") || label.includes("image")) {
    baseIn.payload = {
      reference_images: ["ref_01.jpg", "ref_02.jpg"],
      template: "main + infographic",
    };
    baseOut = {
      status: "success",
      generated_assets: [
        { type: "main", path: "out/main_white_bg.png" },
        { type: "infographic", path: "out/infographic.png" },
      ],
    };
  } else if (label.includes("compliance") || label.includes("guardrail") || label.includes("score")) {
    baseIn.payload = {
      assets_to_score: ["out/main_white_bg.png", "out/infographic.png"],
      rules_document: "guardrails.pdf",
    };
    baseOut = {
      status: "success",
      score: 0.78,
      violations: [
        {
          code: "HEALTH_CLAIM_UNSUBSTANTIATED",
          field: "infographic.headline",
          suggestion: "Replace with structure/function language",
        },
        {
          code: "MAIN_IMAGE_NOT_WHITE_BG",
          field: "main.background",
          suggestion: "Remove lifestyle props; use pure white (#FFFFFF)",
        },
      ],
    };
  } else if (label.includes("report") || label.includes("delivery")) {
    baseOut = {
      status: "success",
      submission_ready: false,
      report: { blocking: 2, warnings: 1, fix_suggestions: 2 },
    };
  } else if (label.includes("index") || label.includes("guardrail")) {
    baseIn.payload = {
      document: "guardrails.pdf",
      action: "chunk_and_index",
    };
    baseOut = {
      status: "success",
      index_id: "guardrails_v3",
      rule_count: 42,
      searchable_fields: ["claim_language", "image_background", "prohibited_terms"],
    };
  } else if (label.includes("pdp")) {
    baseIn.payload = {
      reference_images: ["ref_01.jpg"],
      sku: "SKU-8842",
      templates: ["amazon_main", "infographic"],
    };
    baseOut = {
      status: "success",
      generated_assets: [{ type: "pdp_image", path: "out/pdp_render.png" }],
    };
  }

  return { inputJson: baseIn, outputJson: baseOut };
}

export function mockRuntimeForNode(
  node: GraphNode,
  plan?: ArchitecturePlan
): NodeRuntimeMeta {
  const h = hash(node.id);
  const retries = h % 7 === 0 ? 1 : 0;
  const catalogNotes = node.metadata?.catalog_notes;
  const subAgents = parseSubcomponents(
    typeof catalogNotes === "string" ? catalogNotes : undefined,
  );
  let tools = subAgents.length
    ? subAgents
    : TOOL_POOL.filter((_, i) => (h >> i) & 1).slice(0, 3);
  if (!tools.length) tools.push(TOOL_POOL[h % TOOL_POOL.length]);

  const built = buildNodeIoPayload(node, plan);
  const { inputJson, outputJson } = applySavedJsonOverrides(
    node.metadata || {},
    built,
  );
  const catalogLists = catalogListsFromMeta(node.metadata || {});

  return {
    status: "idle",
    latencyMs: 420 + (h % 380),
    retries,
    tools,
    inputs: catalogLists.inputs.length
      ? catalogLists.inputs
      : Object.keys(inputJson),
    outputs: catalogLists.outputs.length
      ? catalogLists.outputs
      : Object.keys(outputJson),
    inputJson,
    outputJson,
    catalog: node.catalog_agent_id,
    project: node.source_project,
  };
}
