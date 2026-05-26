import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import type { FlowNodeData } from "@/types/plan";
import { MetricChips, NodeShell, StatusDot } from "@/components/nodes/shared";

export function InputNode({ data, selected }: NodeProps<Node<FlowNodeData>>) {
  return (
    <NodeShell
      className="border-input/50 bg-gradient-to-br from-slate-800/90 to-slate-900/95 shadow-glass"
      active={data.isActive}
      highlighted={data.isHighlighted || selected}
    >
      <Handle type="source" position={Position.Right} className="!bg-slate-400 !w-2 !h-2" />
      <div className="p-3">
        <div className="flex items-center justify-between gap-2">
          <span className="text-[10px] font-bold tracking-widest text-slate-400">INPUT</span>
          <StatusDot status={data.runtime.status} />
        </div>
        <p className="mt-1 text-sm font-semibold text-white leading-snug">{data.label}</p>
        {data.description && (
          <p
            className={`mt-1 text-[11px] text-slate-400 ${
              data.expanded ? "" : "line-clamp-2"
            }`}
          >
            {data.description}
          </p>
        )}
        <MetricChips runtime={data.runtime} />
      </div>
    </NodeShell>
  );
}
