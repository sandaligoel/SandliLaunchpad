import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import type { FlowNodeData } from "@/architecture-flow/types/plan";
import { NodeShell } from "@/architecture-flow/components/nodes/shared";

export function MergeNode({ data, selected }: NodeProps<Node<FlowNodeData>>) {
  const isDecision = data.kind === "decision";
  return (
    <NodeShell
      className={`shadow-glass ${
        isDecision
          ? "border-amber-500/50 bg-gradient-to-br from-amber-950/80 to-slate-900/90"
          : "border-purple-500/50 bg-gradient-to-br from-purple-950/80 to-slate-900/90"
      }`}
      active={data.isActive}
      dimmed={data.isDimmed}
      highlighted={data.isHighlighted || selected}
    >
      <Handle type="target" position={Position.Left} className="!w-2 !h-2" />
      <Handle type="source" position={Position.Right} className="!w-2 !h-2" />
      <div className="p-3">
        <span className="text-[10px] font-bold tracking-widest text-purple-300">
          {isDecision ? "DECISION GATE" : "MERGE"}
        </span>
        <p className="mt-1 text-sm font-semibold text-white">{data.label}</p>
      </div>
    </NodeShell>
  );
}
