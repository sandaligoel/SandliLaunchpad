import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import type { FlowNodeData } from "@/types/plan";
import { MetricChips, NodeShell, StatusDot } from "@/components/nodes/shared";

export function HumanNode({ data, selected }: NodeProps<Node<FlowNodeData>>) {
  return (
    <NodeShell
      className="border-hitl/60 bg-gradient-to-br from-orange-950/85 to-slate-900/90 shadow-glass"
      active={data.isActive}
      dimmed={data.isDimmed}
      highlighted={data.isHighlighted || selected}
    >
      <Handle type="target" position={Position.Left} className="!bg-orange-400 !w-2 !h-2" />
      <Handle type="source" position={Position.Top} id="retry" className="!bg-orange-300 !w-2 !h-2 !left-1/2" />
      <div className="p-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">👤</span>
          <div>
            <span className="text-[10px] font-bold tracking-widest text-orange-300">HUMAN GATE</span>
            <p className="text-sm font-semibold text-white">{data.label}</p>
          </div>
          <StatusDot status={data.runtime.status} />
        </div>
        <MetricChips runtime={data.runtime} />
      </div>
    </NodeShell>
  );
}
