import {
  BaseEdge,
  EdgeLabelRenderer,
  getSmoothStepPath,
  type Edge,
  type EdgeProps,
} from "@xyflow/react";
import type { FlowEdgeData } from "@/types/plan";

const STROKE: Record<FlowEdgeData["edgeKind"], string> = {
  sequential: "#3b82f6",
  parallel: "#22d3ee",
  merge: "#a855f7",
  retry: "#f97316",
  data: "#64748b",
};

const OFFSET: Record<FlowEdgeData["edgeKind"], number> = {
  sequential: 18,
  parallel: 28,
  merge: 22,
  retry: 20,
  data: 14,
};

export function AnimatedEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  label,
}: EdgeProps<Edge<FlowEdgeData>>) {
  const kind = data?.edgeKind ?? "sequential";
  const stroke = STROKE[kind];
  const active = data?.isActive;

  const [path, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    borderRadius: kind === "merge" ? 20 : 14,
    offset: OFFSET[kind],
  });

  return (
    <>
      <BaseEdge
        id={id}
        path={path}
        style={{
          stroke,
          strokeWidth: active ? 3 : 2,
          opacity: active ? 1 : 0.7,
        }}
      />
      <path
        d={path}
        fill="none"
        stroke={stroke}
        strokeWidth={active ? 2.5 : 1.5}
        strokeDasharray={kind === "parallel" ? "10 7" : kind === "retry" ? "5 5" : "none"}
        className={active ? "animate-flow-dash opacity-90" : "opacity-30"}
        style={{ pointerEvents: "none" }}
      />
      {(label || data?.label) && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: "absolute",
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: "all",
            }}
            className="rounded bg-panel/95 px-1.5 py-0.5 text-[9px] font-medium text-slate-400 border border-border shadow-sm"
          >
            {String(label || data?.label)}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
