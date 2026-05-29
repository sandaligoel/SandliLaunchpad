import { MarkerType, type DefaultEdgeOptions, type Edge } from "@xyflow/react";
import { workflowTheme } from "@/utils/workflowTheme";

export const WORKFLOW_EDGE_COLOR = workflowTheme.edge.strokeEnd;
export const WORKFLOW_EDGE_COLOR_SELECTED = workflowTheme.edge.selected;

export const WORKFLOW_EDGE_MARKER = {
  type: MarkerType.ArrowClosed,
  color: workflowTheme.edge.strokeEnd,
  width: 22,
  height: 22,
} as const;

export const workflowDefaultEdgeOptions: DefaultEdgeOptions = {
  type: "pipeline",
  sourceHandle: "out",
  targetHandle: "in",
  animated: false,
  style: {
    stroke: workflowTheme.edge.stroke,
    strokeWidth: workflowTheme.edge.width,
  },
  markerEnd: WORKFLOW_EDGE_MARKER,
};

export type GraphEdgeInput = {
  from_id: string;
  to_id: string;
  label?: string | null;
};

/** Pipeline edge with stable handle ids and spread for parallel links. */
export function buildWorkflowEdge(
  edge: GraphEdgeInput,
  indexInGroup: number,
  groupSize: number,
  sourceRow = 0,
  targetRow = 0,
): Edge {
  const spread =
    groupSize > 1 ? (indexInGroup - (groupSize - 1) / 2) * 0.22 : 0;
  const rowTilt = (targetRow - sourceRow) * 0.04;

  return {
    id: `e-${edge.from_id}-${edge.to_id}`,
    source: edge.from_id,
    target: edge.to_id,
    sourceHandle: "out",
    targetHandle: "in",
    type: "pipeline",
    label: edge.label?.trim() || undefined,
    data: {
      edgeLabel: edge.label?.trim() || undefined,
      spread,
      rowTilt,
    },
    animated: false,
    style: {
      stroke: workflowTheme.edge.stroke,
      strokeWidth: workflowTheme.edge.width,
      strokeLinecap: "round",
      strokeLinejoin: "round",
    },
    markerEnd: { ...WORKFLOW_EDGE_MARKER },
    zIndex: 1,
    interactionWidth: 24,
  };
}

export function groupEdgesBySource(
  edges: GraphEdgeInput[],
): Map<string, GraphEdgeInput[]> {
  const map = new Map<string, GraphEdgeInput[]>();
  for (const e of edges) {
    const list = map.get(e.from_id) ?? [];
    list.push(e);
    map.set(e.from_id, list);
  }
  for (const [from, list] of map) {
    list.sort((a, b) => a.to_id.localeCompare(b.to_id));
    map.set(from, list);
  }
  return map;
}

export const workflowZoomConfig = {
  minZoom: 0.05,
  maxZoom: 50,
  zoomFactor: 1.15,
  zoomOnScrollSpeed: 0.75,
  fitViewPadding: 0.2,
  fitViewDuration: 350,
  fullscreenFitPadding: 0.12,
  fullscreenFitDuration: 450,
  presetLevels: [0.5, 0.75, 1, 1.5, 2] as const,
} as const;

export function fitWorkflowToView(
  fitView: (options?: {
    padding?: number;
    duration?: number;
    minZoom?: number;
    maxZoom?: number;
  }) => void,
  fullscreen = false,
) {
  fitView({
    padding: fullscreen
      ? workflowZoomConfig.fullscreenFitPadding
      : workflowZoomConfig.fitViewPadding,
    duration: fullscreen
      ? workflowZoomConfig.fullscreenFitDuration
      : workflowZoomConfig.fitViewDuration,
    minZoom: workflowZoomConfig.minZoom,
  });
}
