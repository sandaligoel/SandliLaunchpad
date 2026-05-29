import { type Node, type NodeProps } from "@xyflow/react";
import type { FlowNodeData } from "@/architecture-flow/types/plan";

export function LaneLabelNode({ data }: NodeProps<Node<FlowNodeData>>) {
  return (
    <div className="pointer-events-none select-none">
      <span className="text-[11px] font-bold tracking-[0.2em] text-slate-600">{data.label}</span>
    </div>
  );
}
