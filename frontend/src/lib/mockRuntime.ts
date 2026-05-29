import type { ArchitecturePlan, GraphNode, NodeRuntimeMeta } from "@/types/plan";

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

/** Build display payloads for Step Details / node inspector (from plan graph). */
export function buildNodeIoPayload(
  node: GraphNode,
  plan?: ArchitecturePlan
): { inputJson: Record<string, unknown>; outputJson: Record<string, unknown> } {
  const label = (node.label || node.id || "step").toLowerCase();
  const upstream = upstreamLabels(plan, node.id);
  const meta = node.metadata || {};
  const capability = meta.capability || node.id;

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
  const tools = TOOL_POOL.filter((_, i) => (h >> i) & 1).slice(0, 3);
  if (!tools.length) tools.push(TOOL_POOL[h % TOOL_POOL.length]);

  const { inputJson, outputJson } = buildNodeIoPayload(node, plan);

  return {
    status: "idle",
    latencyMs: 0,
    retries,
    tools,
    inputs: Object.keys(inputJson),
    outputs: Object.keys(outputJson),
    inputJson,
    outputJson,
    catalog: node.catalog_agent_id,
    project: node.source_project,
  };
}
