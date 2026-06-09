import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import type { FlowNodeData } from "@/architecture-flow/types/plan";
import { KIND_META } from "@/utils/agentKind";
import { KindNodeChrome, NodeShell } from "@/architecture-flow/components/nodes/shared";

export function MergeNode({ data, selected }: NodeProps<Node<FlowNodeData>>) {
  const isDecision = data.kind === "decision";
  const kind = data.implementationKind;
  const meta = kind ? KIND_META[kind] : null;

  return (
    <NodeShell
      className={`shadow-glass overflow-hidden ${
        isDecision
          ? "border-amber-500/50"
          : kind
            ? ""
            : "border-purple-500/50"
      }`}
      active={data.isActive}
      dimmed={data.isDimmed}
      highlighted={data.isHighlighted || selected}
      kindBorder={meta?.border}
      kindGlow={meta?.glow}
    >
      <Handle type="target" position={Position.Left} className="!w-2.5 !h-2.5" />
      <Handle type="source" position={Position.Right} className="!w-2.5 !h-2.5" />
      <div
        className={
          kind
            ? undefined
            : `bg-gradient-to-br ${
                isDecision
                  ? "from-amber-950/80 to-slate-900/90"
                  : "from-purple-950/80 to-slate-900/90"
              }`
        }
        style={meta ? { background: meta.nodeBg } : undefined}
      >
        <KindNodeChrome
          kind={kind}
          roleLabel={
            !kind ? (
              <span className="text-[10px] font-bold tracking-widest text-purple-300">
                {isDecision ? "DECISION GATE" : "MERGE"}
              </span>
            ) : undefined
          }
        >
          <p className="text-[15px] font-bold text-white leading-snug">{data.label}</p>
          {data.description ? (
            <p className="mt-1 text-[11px] text-slate-300 line-clamp-2">{data.description}</p>
          ) : null}
        </KindNodeChrome>
      </div>
    </NodeShell>
  );
}
