import { ViewportPortal, useNodes } from "@xyflow/react";
import type { FlowNodeData } from "@/types/plan";
import { LAYOUT } from "@/layout/constants";

export function LayoutDebugOverlay({ enabled }: { enabled: boolean }) {
  const nodes = useNodes();
  if (!enabled) return null;

  return (
    <ViewportPortal>
      {nodes.map((n) => {
        const d = n.data as FlowNodeData;
        if (d.kind === "lane-band" || d.kind === "lane-label" || d.kind === "parallel-group") {
          return null;
        }
        const w = Number(n.style?.width) || d.measuredWidth || LAYOUT.defaultNodeWidth;
        const h = Number(n.style?.height) || d.measuredHeight || LAYOUT.minNodeHeight;
        return (
          <div
            key={`dbg_${n.id}`}
            className="pointer-events-none"
            style={{
              position: "absolute",
              left: n.position.x,
              top: n.position.y,
              width: w,
              height: h,
              border: "1px dashed rgba(248,113,113,0.7)",
              borderRadius: 12,
              boxSizing: "border-box",
            }}
          />
        );
      })}
    </ViewportPortal>
  );
}
