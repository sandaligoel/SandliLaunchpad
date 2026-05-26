import type { GraphNode, NodeRuntimeMeta } from "@/types/plan";

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

export function mockRuntimeForNode(node: GraphNode): NodeRuntimeMeta {
  const h = hash(node.id);
  const latencyMs = 120 + (h % 900);
  const retries = h % 7 === 0 ? 1 : 0;
  const tools = TOOL_POOL.filter((_, i) => (h >> i) & 1).slice(0, 3);
  if (!tools.length) tools.push(TOOL_POOL[h % TOOL_POOL.length]);

  return {
    status: "idle",
    latencyMs,
    retries,
    tools,
    inputs: node.type === "data_store" ? ["PDF", "API", "Assets"] : ["upstream payload"],
    outputs:
      node.type === "human"
        ? ["approval decision"]
        : node.type === "orchestrator"
          ? ["routing plan"]
          : ["structured result"],
    catalog: node.catalog_agent_id,
    project: node.source_project,
  };
}
