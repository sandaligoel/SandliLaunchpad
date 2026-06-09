import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import type { FlowNodeData } from "@/architecture-flow/types/plan";
import { KindNodeChrome, NodeShell, StatusDot } from "@/architecture-flow/components/nodes/shared";

export function HumanNode({ data, selected }: NodeProps<Node<FlowNodeData>>) {
  return (
    <NodeShell
      className="border-orange-500/70 shadow-glass overflow-hidden"
      active={data.isActive}
      dimmed={data.isDimmed}
      highlighted={data.isHighlighted || selected}
      kindBorder="rgba(251,146,60,0.9)"
      kindGlow="rgba(251,146,60,0.45)"
    >
      <Handle type="target" position={Position.Left} id="in" className="!w-2.5 !h-2.5" />
      <Handle type="source" position={Position.Right} id="out" className="!w-2.5 !h-2.5" />
      <Handle
        type="source"
        position={Position.Top}
        id="retry"
        className="!bg-orange-300 !w-2 !h-2 !left-1/2"
      />
      <div className="bg-gradient-to-br from-orange-950/90 to-slate-900/95">
        <div className="absolute inset-x-0 top-0 h-2.5 bg-gradient-to-r from-orange-600 to-amber-500 shadow-[0_0_14px_rgba(251,146,60,0.5)]" />
        <div className="absolute left-0 top-0 bottom-0 w-[5px] bg-gradient-to-b from-orange-500 to-amber-600" />
        <KindNodeChrome
          roleLabel={
            <span className="inline-flex items-center gap-1.5 rounded-md border-2 border-orange-400/80 bg-orange-500/25 px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-widest text-orange-100 shadow-[0_0_12px_rgba(251,146,60,0.4)]">
              👤 Human gate
            </span>
          }
        >
          <div className="flex items-start justify-between gap-2">
            <p className="text-[15px] font-bold text-white leading-snug">{data.label}</p>
            <StatusDot status={data.runtime.status} />
          </div>
          {data.description ? (
            <p className="mt-1.5 text-[11px] text-orange-100/80 line-clamp-2">
              {data.description}
            </p>
          ) : null}
        </KindNodeChrome>
      </div>
    </NodeShell>
  );
}
