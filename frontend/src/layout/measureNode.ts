import type { Node } from "@xyflow/react";
import type { FlowNodeData } from "@/types/plan";
import { LAYOUT } from "@/layout/constants";

export interface NodeDimensions {
  width: number;
  height: number;
}

function lineCount(text: string, charsPerLine: number, maxLines: number): number {
  if (!text.trim()) return 0;
  return Math.min(maxLines, Math.ceil(text.length / charsPerLine));
}

export function measureNode(node: Node<FlowNodeData>): NodeDimensions {
  const { data } = node;
  const kind = data.kind;
  const label = (data.label || "").trim();
  const desc = data.expanded ? (data.description || "").trim() : "";
  const clampedDesc = data.expanded
    ? desc
    : (data.description || "").trim().slice(0, 120);

  let width: number = LAYOUT.defaultNodeWidth;
  let height: number = LAYOUT.minNodeHeight;

  const labelLines = lineCount(label, 26, 3);
  height += Math.max(0, labelLines - 1) * 20;

  if (kind === "orchestrator") {
    width = 272;
    height = Math.max(height, 108);
    const descLines = lineCount(clampedDesc, 38, data.expanded ? 4 : 2);
    height += descLines * 14;
  } else if (kind === "input") {
    width = 260;
    const descLines = lineCount(clampedDesc, 36, LAYOUT.maxDescLines);
    height += descLines * 14;
  } else if (kind === "human") {
    width = 256;
    height = Math.max(height, 96);
  } else if (kind === "merge" || kind === "decision") {
    width = 252;
    height = Math.max(height, 92);
  } else if (kind === "parallel-group") {
    return { width: 400, height: 48 };
  } else if (kind === "lane-label" || kind === "lane-band") {
    return { width: LAYOUT.laneLabelWidth, height: 24 };
  } else {
    if (data.branchLabel) height += 14;
    if (data.runtime.catalog) height += 18;
    height += 28;
    const descLines = lineCount(clampedDesc, 34, LAYOUT.maxDescLines);
    height += descLines * 13;
    if (data.expanded) height += 72;
  }

  width = Math.min(320, Math.max(width, 220 + Math.min(40, label.length)));
  height = Math.max(LAYOUT.minNodeHeight, Math.ceil(height));

  return { width, height };
}

export function applyMeasuredDimensions(
  nodes: Node<FlowNodeData>[]
): Map<string, NodeDimensions> {
  const map = new Map<string, NodeDimensions>();
  for (const n of nodes) {
    if (n.id.startsWith("__lane_")) continue;
    const dim = measureNode(n);
    map.set(n.id, dim);
    n.style = { ...n.style, width: dim.width, height: dim.height };
    n.data = {
      ...n.data,
      measuredWidth: dim.width,
      measuredHeight: dim.height,
    };
  }
  return map;
}
