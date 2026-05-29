import ELK from "elkjs/lib/elk.bundled.js";
import type { Edge, Node } from "@xyflow/react";
import type { FlowEdgeData, FlowNodeData } from "@/architecture-flow/types/plan";
import type { NodeDimensions } from "@/architecture-flow/layout/measureNode";
import { LAYOUT } from "@/architecture-flow/layout/constants";

const elk = new ELK();

export interface ElkLayoutResult {
  positions: Map<string, { x: number; y: number }>;
  width: number;
  height: number;
}

/**
 * ELK layered layout for a subset of nodes (one lane or parallel fork).
 */
export async function layoutSubgraphWithElk(
  nodeIds: string[],
  _allNodes: Node<FlowNodeData>[],
  allEdges: Edge<FlowEdgeData>[],
  sizes: Map<string, NodeDimensions>,
  direction: "RIGHT" | "DOWN" = "RIGHT"
): Promise<ElkLayoutResult> {
  const idSet = new Set(nodeIds);
  const children = nodeIds
    .filter((id) => sizes.has(id))
    .map((id) => {
      const dim = sizes.get(id)!;
      return {
        id,
        width: dim.width,
        height: dim.height,
      };
    });

  const elkEdges = allEdges
    .filter((e) => idSet.has(e.source) && idSet.has(e.target))
    .map((e) => ({
      id: e.id,
      sources: [e.source],
      targets: [e.target],
    }));

  const graph = {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": direction,
      "elk.spacing.nodeNode": String(LAYOUT.nodeGapX),
      "elk.layered.spacing.nodeNodeBetweenLayers": String(LAYOUT.nodeGapX + 24),
      "elk.layered.spacing.edgeNodeBetweenLayers": "48",
      "elk.edgeRouting": "ORTHOGONAL",
      "elk.layered.mergeEdges": "true",
      "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
      "elk.padding": `[top=${LAYOUT.lanePadY},left=${LAYOUT.lanePadX},bottom=${LAYOUT.lanePadY},right=${LAYOUT.lanePadX}]`,
    },
    children,
    edges: elkEdges,
  };

  const layouted = await elk.layout(graph);
  const positions = new Map<string, { x: number; y: number }>();

  let maxX = 0;
  let maxY = 0;
  for (const child of layouted.children ?? []) {
    const x = child.x ?? 0;
    const y = child.y ?? 0;
    const w = child.width ?? LAYOUT.defaultNodeWidth;
    const h = child.height ?? LAYOUT.minNodeHeight;
    positions.set(child.id, { x, y });
    maxX = Math.max(maxX, x + w);
    maxY = Math.max(maxY, y + h);
  }

  return {
    positions,
    width: maxX + LAYOUT.lanePadX,
    height: maxY + LAYOUT.lanePadY,
  };
}
