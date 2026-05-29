import { type Edge, type Node } from "@xyflow/react";
import type {
  GraphDraft,
  GraphEdge,
  GraphNode,
  ReuseDecision,
  ValidationLevel,
} from "@/api/affine/types";
import {
  buildWorkflowEdge,
  groupEdgesBySource,
} from "@/utils/flowEdgeStyles";
import { sanitizeGraphDraft } from "@/utils/graphSanitize";

const LAYER_GAP_X = 520;
const MIN_NODE_GAP_Y = 56;
const CANVAS_PAD_X = 120;
const CANVAS_PAD_Y = 90;
/** Must match LaunchpadPlanNode width in CSS (react-flow uses this for layout). */
export const NODE_WIDTH = 300;
const MIN_NODE_HEIGHT = 176;

function estimateNodeHeight(node: GraphNode): number {
  const labelChars = (node.label || "").length;
  const descChars = (node.description || "").length;

  const labelLines = Math.max(1, Math.ceil(labelChars / 34));
  const descLines = Math.ceil(descChars / 46);

  // Base shell + icon/meta/chip + body lines.
  const estimated =
    124 + labelLines * 18 + Math.min(descLines, 7) * 16;
  return Math.max(MIN_NODE_HEIGHT, estimated);
}

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

function assignLayers(
  nodeIds: string[],
  edges: { from_id: string; to_id: string }[],
): Map<string, number> {
  const preds = new Map<string, string[]>();
  for (const id of nodeIds) preds.set(id, []);
  for (const e of edges) {
    if (!preds.has(e.to_id)) preds.set(e.to_id, []);
    preds.get(e.to_id)!.push(e.from_id);
  }

  const layer = new Map<string, number>();
  const order: string[] = [];
  const indegree = new Map(nodeIds.map((id) => [id, 0]));
  const adj = new Map<string, string[]>();
  for (const id of nodeIds) adj.set(id, []);
  for (const e of edges) {
    if (!adj.has(e.from_id)) continue;
    adj.get(e.from_id)!.push(e.to_id);
    indegree.set(e.to_id, (indegree.get(e.to_id) ?? 0) + 1);
  }
  const queue = nodeIds.filter((id) => (indegree.get(id) ?? 0) === 0);
  if (queue.length === 0 && nodeIds.length > 0) queue.push(nodeIds[0]!);
  while (queue.length > 0) {
    const id = queue.shift()!;
    order.push(id);
    for (const nxt of adj.get(id) ?? []) {
      const d = (indegree.get(nxt) ?? 0) - 1;
      indegree.set(nxt, d);
      if (d === 0) queue.push(nxt);
    }
  }
  for (const id of nodeIds) {
    if (!order.includes(id)) order.push(id);
  }

  for (const id of order) {
    const ps = preds.get(id) ?? [];
    layer.set(
      id,
      ps.length === 0 ? 0 : 1 + Math.max(...ps.map((p) => layer.get(p) ?? 0)),
    );
  }
  return layer;
}

/** Reduce edge crossings by aligning nodes with their neighbours. */
function orderLayersByBarycenter(
  byLayer: Map<number, GraphNode[]>,
  edges: GraphEdge[],
): Map<number, GraphNode[]> {
  const maxLayer = Math.max(0, ...byLayer.keys());
  const nodeById = new Map<string, GraphNode>();
  for (const nodes of byLayer.values()) {
    for (const n of nodes) nodeById.set(n.id, n);
  }

  const indexInLayer = (layer: number, id: string): number => {
    const list = byLayer.get(layer) ?? [];
    return list.findIndex((n) => n.id === id);
  };

  const sortLayer = (layer: number, scores: Map<string, number>) => {
    const nodes = byLayer.get(layer);
    if (!nodes?.length) return;
    const sorted = [...nodes].sort(
      (a, b) => (scores.get(a.id) ?? 0) - (scores.get(b.id) ?? 0),
    );
    byLayer.set(layer, sorted);
  };

  for (let pass = 0; pass < 4; pass++) {
    for (let layer = 1; layer <= maxLayer; layer++) {
      const scores = new Map<string, number>();
      for (const node of byLayer.get(layer) ?? []) {
        const preds = edges
          .filter((e) => e.to_id === node.id)
          .map((e) => e.from_id);
        if (preds.length === 0) {
          scores.set(node.id, indexInLayer(layer, node.id));
        } else {
          const avg =
            preds.reduce(
              (s, p) => s + indexInLayer(layer - 1, p),
              0,
            ) / preds.length;
          scores.set(node.id, avg);
        }
      }
      sortLayer(layer, scores);
    }

    for (let layer = maxLayer - 1; layer >= 0; layer--) {
      const scores = new Map<string, number>();
      for (const node of byLayer.get(layer) ?? []) {
        const succs = edges
          .filter((e) => e.from_id === node.id)
          .map((e) => e.to_id);
        if (succs.length === 0) {
          scores.set(node.id, indexInLayer(layer, node.id));
        } else {
          const avg =
            succs.reduce(
              (s, p) => s + indexInLayer(layer + 1, p),
              0,
            ) / succs.length;
          scores.set(node.id, avg);
        }
      }
      sortLayer(layer, scores);
    }
  }

  return byLayer;
}

export type ArchitectureNodeData = {
  label: string;
  nodeType: string;
  decision: string;
  agentId?: string | null;
  agentName?: string | null;
  rationale?: string;
  description?: string | null;
  inputs?: string[];
  outputs?: string[];
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
  nodeIo?: Record<string, { inputs: string[]; outputs: string[] }>,
): { nodes: Node[]; edges: Edge[] } {
  const clean = sanitizeGraphDraft(graph);
  const nodeIds = clean.nodes.map((n) => n.id);
  const layerOf = assignLayers(nodeIds, clean.edges);

  let byLayer = new Map<number, GraphNode[]>();
  for (const node of clean.nodes) {
    const l = layerOf.get(node.id) ?? 0;
    if (!byLayer.has(l)) byLayer.set(l, []);
    byLayer.get(l)!.push(node);
  }
  byLayer = orderLayersByBarycenter(byLayer, clean.edges);

  const maxRows = Math.max(
    1,
    ...[...byLayer.values()].map((nodes) => nodes.length),
  );
  const maxNodeHeight = Math.max(
    MIN_NODE_HEIGHT,
    ...clean.nodes.map(estimateNodeHeight),
  );
  const rowStride = maxNodeHeight + MIN_NODE_GAP_Y;

  const rowOf = new Map<string, number>();
  const flowNodes: Node[] = [];

  for (const [layer, nodesInLayer] of [...byLayer.entries()].sort(
    (a, b) => a[0] - b[0],
  )) {
    const columnHeight = (nodesInLayer.length - 1) * rowStride;
    const totalCanvasHeight = Math.max(maxRows * rowStride, rowStride);
    const yOffset =
      CANVAS_PAD_Y + (totalCanvasHeight - (columnHeight + maxNodeHeight)) / 2;

    nodesInLayer.forEach((node, row) => {
      rowOf.set(node.id, row);
      const decision = decisionForNode(node.id, decisions);
      const isSelected = node.id === selectedNodeId;
      const validationLevel = nodeStatus[node.id];
      const override = positionOverrides?.[node.id];
      const io = nodeIo?.[node.id];
      const savedIn = node.inputs?.filter((s) => s.trim()) ?? [];
      const savedOut = node.outputs?.filter((s) => s.trim()) ?? [];
      flowNodes.push({
        id: node.id,
        type: "launchpad",
        position: override ?? {
          x: CANVAS_PAD_X + layer * LAYER_GAP_X,
          y: yOffset + row * rowStride,
        },
        width: NODE_WIDTH,
        style: { width: NODE_WIDTH },
        selected: isSelected,
        data: {
          label: node.label,
          nodeType: node.type,
          agentId: node.agent_id,
          description: node.description,
          decision: decision?.decision ?? (node.agent_id ? "reuse" : "build"),
          agentName: decision?.agent_name,
          rationale: decision?.rationale,
          inputs: savedIn.length ? savedIn : io?.inputs,
          outputs: savedOut.length ? savedOut : io?.outputs,
          layer: layer + 1,
          selected: isSelected,
          validationLevel,
        } satisfies ArchitectureNodeData,
      });
    });
  }

  const bySource = groupEdgesBySource(clean.edges);
  const flowEdges: Edge[] = [];
  for (const [, group] of bySource) {
    const sorted = [...group].sort(
      (a, b) => (rowOf.get(a.to_id) ?? 0) - (rowOf.get(b.to_id) ?? 0),
    );
    sorted.forEach((e, i) => {
      flowEdges.push(
        buildWorkflowEdge(
          e,
          i,
          sorted.length,
          rowOf.get(e.from_id) ?? 0,
          rowOf.get(e.to_id) ?? 0,
        ),
      );
    });
  }

  return { nodes: flowNodes, edges: flowEdges };
}
