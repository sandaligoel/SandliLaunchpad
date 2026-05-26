import { type Node, type NodeProps } from "@xyflow/react";
import type { FlowNodeData } from "@/types/plan";

export function ParallelGroupNode({ data }: NodeProps<Node<FlowNodeData>>) {
  return (
    <div className="h-full w-full rounded-2xl border border-dashed border-cyan-500/40 bg-cyan-950/20 backdrop-blur-sm">
      <div className="absolute -top-3 left-4 rounded-md bg-cyan-500/20 px-2 py-0.5 text-[10px] font-bold tracking-wide text-cyan-300">
        ⚡ PARALLEL GROUP
      </div>
      <p className="px-4 pt-4 text-xs font-medium text-cyan-200/80">{data.label}</p>
    </div>
  );
}
