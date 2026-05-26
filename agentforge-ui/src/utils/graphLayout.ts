import { MarkerType, type Edge, type Node } from "@xyflow/react";
import type {
  GraphDraft,
  GraphNode,
  ReuseDecision,
  ValidationLevel,
} from "@/api/affine/types";

const LAYER_GAP_X = 300;
const NODE_GAP_Y = 120;

const TYPE_ORDER: Record<string, number> = {
  gateway: 0,
  agent: 1,
  custom: 2,
  human: 3,
};

function decisionForNode(
  nodeId: string,
  decisions: ReuseDecision[],
): ReuseDecision | undefined {
  return decisions.find((d) => d.node_id === nodeId);
}

function sortNodesInLayer(nodes: GraphNode[]): GraphNode[] {
  return [...nodes].sort((a, b) => {
    const ta = TYPE_ORDER[a.type] ?? 2;
    const tb = TYPE_ORDER[b.type] ?? 2;
    if (ta !== tb) return ta - tb;
    return a.label.localeCompare(b.label);
  });
}

export type ArchitectureNodeData = {
  label: string;
  nodeType: string;
  decision: string;
  agentId?: string | null;
  agentName?: string | null;
  rationale?: string;
  description?: string | null;
  layer?: number;
  selected?: boolean;
  validationLevel?: ValidationLevel;
};

export function layoutGraphToFlow(
  graph: GraphDraft,
  decisions: ReuseDecision[] = [],
  selectedNodeId: string | null = null,
  nodeStatus: Record<string, ValidationLevel> = {},
  positionOverrides?: Record<string, { x: number; y: number }>,
): { nodes: Node[]; edges: Edge[] } {
  const nodeIds = graph.nodes.map((n) => n.id);
  const inDegree = new Map<string, number>();
  const adj = new Map<string, string[]>();

  for (const id of nodeIds) {
    inDegree.set(id, 0);
    adj.set(id, []);
  }

  for (const edge of graph.edges) {
    if (!adj.has(edge.from_id) || !inDegree.has(edge.to_id)) continue;
    adj.get(edge.from_id)!.push(edge.to_id);
    inDegree.set(edge.to_id, (inDegree.get(edge.to_id) ?? 0) + 1);
  }

  let frontier = nodeIds.filter((id) => (inDegree.get(id) ?? 0) === 0);
  if (frontier.length === 0 && nodeIds.length > 0) {
    frontier = [nodeIds[0]];
  }

  const layerOf = new Map<string, number>();
  let layerIndex = 0;

  while (frontier.length > 0) {
    const next: string[] = [];
    for (const id of frontier) {
      if (layerOf.has(id)) continue;
      layerOf.set(id, layerIndex);
      for (const to of adj.get(id) ?? []) {
        if (!layerOf.has(to)) next.push(to);
      }
    }
    frontier = [...new Set(next)];
    layerIndex += 1;
  }

  for (const id of nodeIds) {
    if (!layerOf.has(id)) layerOf.set(id, layerIndex++);
  }

  const byLayer = new Map<number, GraphNode[]>();
  for (const node of graph.nodes) {
    const l = layerOf.get(node.id) ?? 0;
    if (!byLayer.has(l)) byLayer.set(l, []);
    byLayer.get(l)!.push(node);
  }

  const maxRows = Math.max(
    1,
    ...[...byLayer.values()].map((nodes) => nodes.length),
  );

  const flowNodes: Node[] = [];
  for (const [layer, rawNodes] of [...byLayer.entries()].sort(
    (a, b) => a[0] - b[0],
  )) {
    const nodesInLayer = sortNodesInLayer(rawNodes);
    const columnHeight = (nodesInLayer.length - 1) * NODE_GAP_Y;
    const yOffset = (maxRows * NODE_GAP_Y - columnHeight) / 2;

    nodesInLayer.forEach((node, row) => {
      const decision = decisionForNode(node.id, decisions);
      const isSelected = node.id === selectedNodeId;
      const validationLevel = nodeStatus[node.id];
      const override = positionOverrides?.[node.id];
      flowNodes.push({
        id: node.id,
        type: "launchpad",
        position: override ?? {
          x: layer * LAYER_GAP_X + 40,
          y: yOffset + row * NODE_GAP_Y,
        },
        selected: isSelected,
        data: {
          label: node.label,
          nodeType: node.type,
          agentId: node.agent_id,
          description: node.description,
          decision: decision?.decision ?? (node.agent_id ? "reuse" : "build"),
          agentName: decision?.agent_name,
          rationale: decision?.rationale,
          layer: layer + 1,
          selected: isSelected,
          validationLevel,
        } satisfies ArchitectureNodeData,
      });
    });
  }

  const flowEdges: Edge[] = graph.edges.map((e, i) => ({
    id: `e-${i}-${e.from_id}-${e.to_id}`,
    source: e.from_id,
    target: e.to_id,
    type: "smoothstep",
    label: e.label ?? undefined,
    animated: true,
    style: { stroke: "#1B5E8C", strokeWidth: 2 },
    markerEnd: {
      type: MarkerType.ArrowClosed,
      color: "#1B5E8C",
      width: 18,
      height: 18,
    },
  }));

  return { nodes: flowNodes, edges: flowEdges };
}
