import type { Edge, Node } from "@xyflow/react";
import type { FlowEdgeData, FlowNodeData } from "@/architecture-flow/types/plan";
import { LAYOUT } from "@/architecture-flow/layout/constants";
import { applyMeasuredDimensions } from "@/architecture-flow/layout/measureNode";
import type { ParallelHint } from "@/architecture-flow/lib/buildGraphStructure";
import type { LayoutMeta } from "@/architecture-flow/layout/calculateLayout";

function sortByPipeline(nodes: Node<FlowNodeData>[]): Node<FlowNodeData>[] {
  return [...nodes].sort(
    (a, b) =>
      (a.data.pipelineOrder ?? 0) - (b.data.pipelineOrder ?? 0) ||
      a.id.localeCompare(b.id),
  );
}

/** Group nodes into left-to-right stages; parallel branches share one column. */
function groupStages(
  sorted: Node<FlowNodeData>[],
  parallel: ParallelHint | null,
): Node<FlowNodeData>[][] {
  const parallelSet = new Set(parallel?.branchIds ?? []);
  const stages: Node<FlowNodeData>[][] = [];
  const placed = new Set<string>();

  for (const n of sorted) {
    if (placed.has(n.id)) continue;

    if (parallelSet.has(n.id)) {
      const batch = sorted.filter((x) => parallelSet.has(x.id) && !placed.has(x.id));
      batch.forEach((x) => placed.add(x.id));
      if (batch.length) stages.push(batch);
      continue;
    }

    placed.add(n.id);
    stages.push([n]);
  }

  return stages;
}

/**
 * Single left-to-right pipeline: stages advance on X, parallel branches stack on Y.
 */
export function layoutSequentialPipeline(
  nodes: Node<FlowNodeData>[],
  edges: Edge<FlowEdgeData>[],
  parallel: ParallelHint | null,
): { nodes: Node<FlowNodeData>[]; meta: LayoutMeta } {
  const layoutNodes = nodes.filter(
    (n) =>
      !n.id.startsWith("__lane_") &&
      n.type !== "laneBand" &&
      n.type !== "laneLabel" &&
      n.type !== "parallelGroup",
  );

  const sizes = applyMeasuredDimensions(layoutNodes);
  const sorted = sortByPipeline(layoutNodes);
  const stages = groupStages(sorted, parallel);

  const positions = new Map<string, { x: number; y: number }>();
  const baseY = LAYOUT.marginTop + 80;
  let x = LAYOUT.marginLeft;
  let maxY = baseY;
  let maxX = x;

  for (const stage of stages) {
    const stageWidth = Math.max(...stage.map((n) => sizes.get(n.id)!.width));
    const totalH = stage.reduce((sum, n, i) => {
      const h = sizes.get(n.id)!.height;
      return sum + h + (i > 0 ? LAYOUT.parallelGapY : 0);
    }, 0);

    let y = stage.length > 1 ? baseY - totalH / 2 : baseY;
    for (const n of stage) {
      const dim = sizes.get(n.id)!;
      positions.set(n.id, { x, y });
      y += dim.height + LAYOUT.parallelGapY;
      maxY = Math.max(maxY, y);
    }

    x += stageWidth + LAYOUT.nodeGapX;
    maxX = x;
  }

  const totalWidth = maxX + LAYOUT.marginRight;
  const totalHeight = maxY + LAYOUT.marginBottom;

  const positioned = layoutNodes.map((n) => {
    const dim = sizes.get(n.id)!;
    const pos = positions.get(n.id) ?? { x: LAYOUT.marginLeft, y: baseY };
    return {
      ...n,
      position: pos,
      style: { ...n.style, width: dim.width, height: dim.height },
    };
  });

  const graphBounds = {
    minX: LAYOUT.marginLeft,
    minY: LAYOUT.marginTop,
    maxX: totalWidth,
    maxY: totalHeight,
    width: totalWidth - LAYOUT.marginLeft,
    height: totalHeight - LAYOUT.marginTop,
  };

  return {
    nodes: positioned,
    meta: {
      parallel,
      laneBands: {} as LayoutMeta["laneBands"],
      totalWidth,
      totalHeight,
      bounds: graphBounds,
    },
  };
}
