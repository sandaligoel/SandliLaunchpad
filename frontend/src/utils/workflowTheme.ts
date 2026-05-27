/** Shared workflow canvas palette (edges, nodes, minimap). */
export const workflowTheme = {
  canvasBg: "#eef2f8",
  dot: "#b8c4d4",
  edge: {
    stroke: "#4f46e5",
    strokeEnd: "#0d9488",
    shadow: "rgba(79, 70, 229, 0.22)",
    selected: "#312e81",
    width: 2.5,
    widthSelected: 3.25,
  },
  node: {
    gateway: { accent: "#d97706", soft: "rgba(217, 119, 6, 0.12)" },
    agent: { accent: "#4f46e5", soft: "rgba(79, 70, 229, 0.1)" },
    human: { accent: "#059669", soft: "rgba(5, 150, 105, 0.12)" },
    custom: { accent: "#64748b", soft: "rgba(100, 116, 139, 0.12)" },
  },
} as const;

export function nodeTypeTheme(nodeType: string) {
  const key = nodeType as keyof typeof workflowTheme.node;
  return workflowTheme.node[key] ?? workflowTheme.node.custom;
}
