import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import type { FlowNodeData } from "@/architecture-flow/types/plan";
import { KIND_META } from "@/utils/agentKind";
import { KindNodeChrome, NodeShell, StatusDot } from "@/architecture-flow/components/nodes/shared";

export function InputNode({ data, selected }: NodeProps<Node<FlowNodeData>>) {
  const kind = data.implementationKind ?? "tool";
  const meta = KIND_META[kind];

  return (
    <NodeShell
      className="shadow-glass overflow-hidden"
      active={data.isActive}
      dimmed={data.isDimmed}
      highlighted={data.isHighlighted || selected}
      kindBorder={meta.border}
      kindGlow={meta.glow}
    >
      <Handle type="source" position={Position.Right} id="out" className="!w-2.5 !h-2.5" />
      <KindNodeChrome
        kind={kind}
        roleLabel={
          <span className="text-[10px] font-bold tracking-widest text-slate-300">INPUT</span>
        }
      >
        <div className="flex items-start justify-between gap-2">
          <p className="text-[15px] font-bold text-white leading-snug">{data.label}</p>
          <StatusDot status={data.runtime.status} />
        </div>
        {data.description ? (
          <p
            className={`mt-1.5 text-[11px] text-slate-300 ${
              data.expanded ? "" : "line-clamp-2"
            }`}
          >
            {data.description}
          </p>
        ) : null}
      </KindNodeChrome>
    </NodeShell>
  );
}
