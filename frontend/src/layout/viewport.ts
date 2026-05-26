import type { Node } from "@xyflow/react";
import type { FlowNodeData } from "@/types/plan";
import { LAYOUT } from "@/layout/constants";

/** Readable zoom floor — never compress the graph below this. */
export const VIEWPORT = {
  minZoom: 0.5,
  maxZoom: 2.25,
  fitMinZoom: 0.58,
  fitMaxZoom: 1.05,
  fitPadding: 0.14,
  translatePadX: 1400,
  translatePadY: 900,
  minCanvasWidth: 8000,
  minCanvasHeight: 3200,
};

export interface GraphBounds {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
  width: number;
  height: number;
}

function nodeSize(n: Node<FlowNodeData>): { w: number; h: number } {
  const d = n.data;
  const w =
    Number(n.style?.width) ||
    d.measuredWidth ||
    (n.type === "laneBand" ? 400 : LAYOUT.defaultNodeWidth);
  const h =
    Number(n.style?.height) ||
    d.measuredHeight ||
    (n.type === "laneBand" ? 120 : LAYOUT.minNodeHeight);
  return { w, h };
}

function includeInBounds(n: Node<FlowNodeData>): boolean {
  if (n.id.startsWith("__lane_")) return false;
  return true;
}

export function computeGraphBounds(nodes: Node<FlowNodeData>[]): GraphBounds {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;

  for (const n of nodes) {
    if (!includeInBounds(n)) continue;
    const { w, h } = nodeSize(n);
    minX = Math.min(minX, n.position.x);
    minY = Math.min(minY, n.position.y);
    maxX = Math.max(maxX, n.position.x + w);
    maxY = Math.max(maxY, n.position.y + h);
  }

  if (!Number.isFinite(minX)) {
    return { minX: 0, minY: 0, maxX: 1200, maxY: 800, width: 1200, height: 800 };
  }

  return {
    minX,
    minY,
    maxX,
    maxY,
    width: maxX - minX,
    height: maxY - minY,
  };
}

export function computeTranslateExtent(
  bounds: GraphBounds,
  totalWidth?: number,
  totalHeight?: number
): [[number, number], [number, number]] {
  const extentW = Math.max(
    bounds.maxX + VIEWPORT.translatePadX,
    totalWidth ?? 0,
    VIEWPORT.minCanvasWidth
  );
  const extentH = Math.max(
    bounds.maxY + VIEWPORT.translatePadY,
    totalHeight ?? 0,
    VIEWPORT.minCanvasHeight
  );
  return [
    [bounds.minX - VIEWPORT.translatePadX, bounds.minY - VIEWPORT.translatePadY],
    [extentW, extentH],
  ];
}

export type FitMode = "full" | "orchestrator" | "selection";

export function nodesForFitMode(
  nodes: Node<FlowNodeData>[],
  mode: FitMode,
  selectionIds?: string[]
): Node<FlowNodeData>[] | undefined {
  if (mode === "selection" && selectionIds?.length) {
    const set = new Set(selectionIds);
    const picked = nodes.filter((n) => set.has(n.id) && includeInBounds(n));
    return picked.length ? picked : undefined;
  }

  if (mode === "orchestrator") {
    const orch = nodes.find((n) => n.data.kind === "orchestrator");
    const inputs = nodes.filter((n) => n.data.kind === "input");
    const earlyExec = nodes.filter(
      (n) =>
        n.data.lane === "execution" &&
        (n.data.pipelineOrder ?? 99) <= 4 &&
        n.data.kind !== "parallel-group"
    );
    const merge = nodes.filter(
      (n) => n.data.lane === "merge" || n.data.kind === "decision"
    );
    const picked = [...inputs, ...(orch ? [orch] : []), ...earlyExec, ...merge.slice(0, 2)];
    const uniq = [...new Map(picked.map((n) => [n.id, n])).values()];
    return uniq.length >= 2 ? uniq : undefined;
  }

  return undefined;
}

export const defaultFitViewOptions = {
  padding: VIEWPORT.fitPadding,
  minZoom: VIEWPORT.fitMinZoom,
  maxZoom: VIEWPORT.fitMaxZoom,
  duration: 420,
} as const;
