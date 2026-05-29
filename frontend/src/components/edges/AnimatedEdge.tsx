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
  const flowing = data?.isFlowing;

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
      {active && (
        <path
          d={path}
          fill="none"
          stroke={stroke}
          strokeWidth={8}
          strokeOpacity={0.25}
          style={{ pointerEvents: "none", filter: "blur(4px)" }}
        />
      )}
      <BaseEdge
        id={id}
        path={path}
        style={{
          stroke,
          strokeWidth: active ? 3.5 : 2,
          opacity: active ? 1 : 0.55,
        }}
      />
      <path
        d={path}
        fill="none"
        stroke={flowing ? "#7dd3fc" : stroke}
        strokeWidth={flowing ? 3 : active ? 2.5 : 1.5}
        strokeDasharray={kind === "parallel" ? "10 7" : kind === "retry" ? "5 5" : flowing ? "6 10" : "none"}
        className={
          flowing
            ? "animate-flow-dash opacity-100"
            : active
              ? "animate-flow-dash opacity-80"
              : "opacity-25"
        }
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
            className={`rounded border px-1.5 py-0.5 text-[9px] font-medium shadow-sm ${
              active
                ? "border-blue-500/50 bg-blue-950/95 text-blue-200"
                : "border-border bg-panel/95 text-slate-400"
            }`}
          >
            {String(label || data?.label)}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
