import {
  BaseEdge,
  EdgeLabelRenderer,
  type EdgeProps,
} from "@xyflow/react";
import { workflowTheme } from "@/utils/workflowTheme";
import {
  getWorkflowEdgePath,
  workflowEdgeGradientId,
} from "@/utils/workflowEdgePath";

/**
 * Rounded step connector with gradient stroke and soft shadow (pipeline / architecture flows).
 */
export function FlowPipelineEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  label,
  style,
  markerEnd,
  data,
  selected,
}: EdgeProps) {
  const spread =
    typeof data === "object" &&
    data !== null &&
    "spread" in data &&
    typeof (data as { spread?: number }).spread === "number"
      ? (data as { spread: number }).spread
      : 0;

  const [edgePath, labelX, labelY] = getWorkflowEdgePath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    spread,
  });

  const edgeLabel =
    typeof label === "string"
      ? label.trim()
      : typeof data === "object" &&
          data !== null &&
          "edgeLabel" in data &&
          typeof (data as { edgeLabel?: string }).edgeLabel === "string"
        ? (data as { edgeLabel: string }).edgeLabel.trim()
        : undefined;

  const gradId = workflowEdgeGradientId(id);
  const strokeWidth = selected
    ? workflowTheme.edge.widthSelected
    : workflowTheme.edge.width;

  return (
    <>
      <defs>
        <linearGradient
          id={gradId}
          gradientUnits="userSpaceOnUse"
          x1={sourceX}
          y1={sourceY}
          x2={targetX}
          y2={targetY}
        >
          <stop offset="0%" stopColor={workflowTheme.edge.stroke} />
          <stop offset="100%" stopColor={workflowTheme.edge.strokeEnd} />
        </linearGradient>
      </defs>
      <BaseEdge
        id={`${id}-shadow`}
        path={edgePath}
        style={{
          stroke: workflowTheme.edge.shadow,
          strokeWidth: strokeWidth + 5,
          strokeLinecap: "round",
          strokeLinejoin: "round",
          fill: "none",
          opacity: 0.55,
          ...style,
        }}
        interactionWidth={0}
      />
      <BaseEdge
        id={id}
        path={edgePath}
        className={selected ? "workflow-edge-path--selected" : "workflow-edge-path"}
        style={{
          stroke: selected
            ? workflowTheme.edge.selected
            : `url(#${gradId})`,
          strokeWidth,
          strokeLinecap: "round",
          strokeLinejoin: "round",
          fill: "none",
          ...style,
        }}
        markerEnd={markerEnd}
        interactionWidth={28}
      />
      {edgeLabel ? (
        <EdgeLabelRenderer>
          <div
            className="flow-pipeline-edge-label nodrag nopan"
            title={edgeLabel}
            style={{
              position: "absolute",
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            }}
          >
            <span className="flow-pipeline-edge-label__text">{edgeLabel}</span>
          </div>
        </EdgeLabelRenderer>
      ) : null}
    </>
  );
}
