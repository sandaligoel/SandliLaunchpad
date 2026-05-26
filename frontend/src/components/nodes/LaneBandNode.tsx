import { type Node, type NodeProps } from "@xyflow/react";
import type { FlowNodeData } from "@/types/plan";

export function LaneBandNode(_props: NodeProps<Node<FlowNodeData>>) {
  return (
    <div
      className="h-full w-full rounded-xl border border-slate-700/40 bg-slate-900/25 pointer-events-none"
      style={{
        boxShadow: "inset 0 1px 0 rgba(148,163,184,0.06)",
      }}
    />
  );
}
