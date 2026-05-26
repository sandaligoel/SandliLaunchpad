import type { Edge, Node } from "@xyflow/react";
import type { FlowEdgeData, FlowLane, FlowNodeData } from "@/types/plan";
import { DEBUG_LAYOUT, LANE_ORDER, LANE_LABELS, LAYOUT } from "@/layout/constants";
import { applyMeasuredDimensions, measureNode, type NodeDimensions } from "@/layout/measureNode";
import { logCollisionReport, resolveCollisions, type Bounds } from "@/layout/collision";
import { layoutSubgraphWithElk } from "@/layout/elkLaneLayout";
import type { ParallelHint } from "@/lib/buildGraphStructure";

export interface LayoutMeta {
  parallel: ParallelHint | null;
  laneBands: Record<FlowLane, { y: number; height: number }>;
  totalWidth: number;
  totalHeight: number;
  bounds: {
    minX: number;
    minY: number;
    maxX: number;
    maxY: number;
    width: number;
    height: number;
  };
}

function centerYInLane(laneY: number, laneH: number, nodeH: number): number {
  return laneY + LAYOUT.lanePadY + Math.max(0, (laneH - 2 * LAYOUT.lanePadY - nodeH) / 2);
}

function sortByPipeline(nodes: Node<FlowNodeData>[]): Node<FlowNodeData>[] {
  return [...nodes].sort(
    (a, b) =>
      (a.data.pipelineOrder ?? 0) - (b.data.pipelineOrder ?? 0) ||
      a.id.localeCompare(b.id)
  );
}

async function layoutLaneRow(
  laneNodes: Node<FlowNodeData>[],
  edges: Edge<FlowEdgeData>[],
  sizes: Map<string, NodeDimensions>,
  startX: number,
  laneY: number,
  laneH: number
): Promise<{ positions: Map<string, { x: number; y: number }>; usedWidth: number }> {
  const positions = new Map<string, { x: number; y: number }>();
  if (!laneNodes.length) return { positions, usedWidth: 0 };

  const ids = laneNodes.map((n) => n.id);
  if (ids.length >= 3) {
    const elk = await layoutSubgraphWithElk(ids, laneNodes, edges, sizes, "RIGHT");
    for (const [id, pos] of elk.positions) {
      positions.set(id, { x: startX + pos.x, y: laneY + pos.y });
    }
    return { positions, usedWidth: elk.width + LAYOUT.lanePadX };
  }

  let x = startX + LAYOUT.lanePadX;
  for (const n of sortByPipeline(laneNodes)) {
    const dim = sizes.get(n.id)!;
    positions.set(n.id, { x, y: centerYInLane(laneY, laneH, dim.height) });
    x += dim.width + LAYOUT.nodeGapX;
  }
  return { positions, usedWidth: x - startX };
}

async function layoutParallelFan(
  branchNodes: Node<FlowNodeData>[],
  preNodes: Node<FlowNodeData>[],
  sizes: Map<string, NodeDimensions>,
  startX: number,
  laneY: number,
  laneH: number
): Promise<{
  positions: Map<string, { x: number; y: number }>;
  groupBounds: { x: number; y: number; width: number; height: number };
  usedWidth: number;
}> {
  const positions = new Map<string, { x: number; y: number }>();
  let x = startX + LAYOUT.lanePadX;

  for (const n of sortByPipeline(preNodes)) {
    const dim = sizes.get(n.id)!;
    positions.set(n.id, { x, y: centerYInLane(laneY, laneH, dim.height) });
    x += dim.width + LAYOUT.nodeGapX;
  }

  const branches = sortByPipeline(branchNodes);
  const fanStartX = x + LAYOUT.parallelGapX;
  let bx = fanStartX;
  const fanTop = laneY + LAYOUT.lanePadY;
  let maxBranchH: number = LAYOUT.minNodeHeight;

  for (const n of branches) {
    const dim = sizes.get(n.id)!;
    maxBranchH = Math.max(maxBranchH, dim.height);
    positions.set(n.id, { x: bx, y: fanTop });
    bx += dim.width + LAYOUT.parallelGapX;
  }

  const fanWidth =
    branches.reduce((s, n) => s + sizes.get(n.id)!.width, 0) +
    Math.max(0, branches.length - 1) * LAYOUT.parallelGapX;

  const groupBounds = {
    x: fanStartX - LAYOUT.parallelPad,
    y: fanTop - LAYOUT.parallelPad,
    width: fanWidth + LAYOUT.parallelPad * 2,
    height: maxBranchH + LAYOUT.parallelPad * 2,
  };

  return {
    positions,
    groupBounds,
    usedWidth: fanStartX + fanWidth + LAYOUT.lanePadX - startX,
  };
}

function laneContentHeight(
  laneNodes: Node<FlowNodeData>[],
  sizes: Map<string, NodeDimensions>,
  extra = 0
): number {
  if (!laneNodes.length) return 88;
  const maxH = Math.max(
    ...laneNodes.map((n) => sizes.get(n.id)?.height ?? LAYOUT.minNodeHeight)
  );
  return Math.max(96, maxH + 2 * LAYOUT.lanePadY + extra);
}

export async function calculateLayout(
  nodes: Node<FlowNodeData>[],
  edges: Edge<FlowEdgeData>[],
  parallel: ParallelHint | null
): Promise<{ nodes: Node<FlowNodeData>[]; meta: LayoutMeta }> {
  const layoutNodes = nodes.filter(
    (n) => !n.id.startsWith("__lane_") && n.type !== "laneBand"
  );
  const sizes = applyMeasuredDimensions(layoutNodes);

  const parallelSet = new Set(parallel?.branchIds ?? []);

  const byLane = (lane: FlowLane) =>
    layoutNodes.filter((n) => n.data.lane === lane && n.type !== "parallelGroup");

  const laneBands = {} as LayoutMeta["laneBands"];
  const allPositions = new Map<string, { x: number; y: number }>();
  let currentY = LAYOUT.marginTop;
  let maxContentX = LAYOUT.marginLeft + 480;
  const decorNodes: Node<FlowNodeData>[] = [];

  for (const lane of LANE_ORDER) {
    if (lane === "hitl") currentY += LAYOUT.hitlExtraGap;

    let laneNodes = byLane(lane);

    if (lane === "execution" && parallel && parallel.branchIds.length >= 2) {
      const branchNodes = laneNodes.filter((n) => parallelSet.has(n.id));
      const preNodes = laneNodes.filter((n) => !parallelSet.has(n.id));
      const extra = LAYOUT.parallelPad * 2 + 16;
      const laneH = laneContentHeight([...preNodes, ...branchNodes], sizes, extra);
      laneBands[lane] = { y: currentY, height: laneH };

      const { positions, groupBounds, usedWidth } = await layoutParallelFan(
        branchNodes,
        preNodes,
        sizes,
        LAYOUT.marginLeft,
        currentY,
        laneH
      );
      positions.forEach((v, k) => allPositions.set(k, v));
      maxContentX = Math.max(maxContentX, LAYOUT.marginLeft + usedWidth);

      decorNodes.push({
        id: `__parallel_bg_${parallel.forkAfterId || "root"}`,
        type: "parallelGroup",
        position: { x: groupBounds.x, y: groupBounds.y },
        style: { width: groupBounds.width, height: groupBounds.height, zIndex: -1 },
        selectable: false,
        draggable: false,
        data: {
          kind: "parallel-group",
          label: "Parallel branches",
          lane: "execution",
          runtime: {
            status: "idle",
            latencyMs: 0,
            retries: 0,
            tools: [],
            inputs: [],
            outputs: [],
          },
        },
      });

      currentY += laneH + LAYOUT.laneGap;
      continue;
    }

    const laneH = laneContentHeight(laneNodes, sizes);
    laneBands[lane] = { y: currentY, height: laneH };

    if (laneNodes.length) {
      const { positions, usedWidth } = await layoutLaneRow(
        laneNodes,
        edges,
        sizes,
        LAYOUT.marginLeft,
        currentY,
        laneH
      );
      positions.forEach((v, k) => allPositions.set(k, v));
      maxContentX = Math.max(maxContentX, LAYOUT.marginLeft + usedWidth);
    }

    currentY += laneH + LAYOUT.laneGap;
  }

  const totalWidth = maxContentX + LAYOUT.marginRight;
  const totalHeight = currentY + LAYOUT.marginBottom;

  for (const lane of LANE_ORDER) {
    const band = laneBands[lane];
    if (!band) continue;
    decorNodes.push({
      id: `__band_${lane}`,
      type: "laneBand",
      position: { x: LAYOUT.marginLeft - 20, y: band.y - 10 },
      style: {
        width: totalWidth - LAYOUT.marginLeft + 40,
        height: band.height + 20,
        zIndex: -2,
      },
      selectable: false,
      draggable: false,
      data: {
        kind: "lane-band",
        label: LANE_LABELS[lane],
        lane,
        runtime: {
          status: "idle",
          latencyMs: 0,
          retries: 0,
          tools: [],
          inputs: [],
          outputs: [],
        },
      },
    });
  }

  for (const ln of nodes.filter((n) => n.id.startsWith("__lane_"))) {
    const band = laneBands[ln.data.lane];
    if (band) {
      allPositions.set(ln.id, { x: 24, y: band.y + band.height / 2 - 10 });
    }
  }

  const boxes: Bounds[] = layoutNodes.map((n) => {
    const dim = sizes.get(n.id) ?? measureNode(n);
    const pos = allPositions.get(n.id) ?? { x: LAYOUT.marginLeft, y: currentY };
    return { id: n.id, x: pos.x, y: pos.y, width: dim.width, height: dim.height };
  });

  const resolved = resolveCollisions(boxes);
  if (DEBUG_LAYOUT) logCollisionReport(resolved);
  const resolvedMap = new Map(resolved.map((b) => [b.id, b]));

  let minX = Infinity;
  let minY = Infinity;
  let maxX = 0;
  let maxY = 0;
  for (const b of resolved) {
    minX = Math.min(minX, b.x);
    minY = Math.min(minY, b.y);
    maxX = Math.max(maxX, b.x + b.width);
    maxY = Math.max(maxY, b.y + b.height);
  }
  for (const d of decorNodes) {
    const w = Number(d.style?.width) || 400;
    const h = Number(d.style?.height) || 120;
    minX = Math.min(minX, d.position.x);
    minY = Math.min(minY, d.position.y);
    maxX = Math.max(maxX, d.position.x + w);
    maxY = Math.max(maxY, d.position.y + h);
  }
  const graphBounds = {
    minX: Number.isFinite(minX) ? minX : 0,
    minY: Number.isFinite(minY) ? minY : 0,
    maxX: Number.isFinite(maxX) ? maxX : totalWidth,
    maxY: Number.isFinite(maxY) ? maxY : totalHeight,
    width: Number.isFinite(maxX - minX) ? maxX - minX : totalWidth,
    height: Number.isFinite(maxY - minY) ? maxY - minY : totalHeight,
  };

  const positioned = layoutNodes.map((n) => {
    const box = resolvedMap.get(n.id)!;
    const dim = sizes.get(n.id)!;
    return {
      ...n,
      position: { x: box.x, y: box.y },
      style: { ...n.style, width: dim.width, height: dim.height },
    };
  });

  return {
    nodes: [...decorNodes, ...nodes.filter((n) => n.id.startsWith("__lane_")), ...positioned],
    meta: {
      parallel,
      laneBands,
      totalWidth: Math.max(totalWidth, graphBounds.maxX + LAYOUT.marginRight),
      totalHeight: Math.max(totalHeight, graphBounds.maxY + LAYOUT.marginBottom),
      bounds: graphBounds,
    },
  };
}
