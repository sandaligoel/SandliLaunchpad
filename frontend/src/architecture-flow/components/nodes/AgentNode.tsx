import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import { AnimatePresence, motion } from "framer-motion";
import type { FlowNodeData } from "@/architecture-flow/types/plan";
import {
  KindNodeChrome,
  MetricChips,
  NodeShell,
  ReuseBadge,
  StatusDot,
} from "@/architecture-flow/components/nodes/shared";
import { KIND_META } from "@/utils/agentKind";

const REUSE_STYLES: Record<string, string> = {
  "agent-reuse": "from-emerald-950/50 to-slate-900/90",
  "agent-adapt": "from-teal-950/50 to-slate-900/90",
  "agent-build": "from-indigo-950/50 to-slate-900/90",
};

export function AgentNode({ data, selected }: NodeProps<Node<FlowNodeData>>) {
  const effectiveKind =
    data.implementationKind ?? (data.reuse ? undefined : inferBuildKind(data));
  const kindMeta = effectiveKind ? KIND_META[effectiveKind] : null;
  const reuseGradient = REUSE_STYLES[data.kind] || REUSE_STYLES["agent-build"];

  return (
    <NodeShell
      className="shadow-glass overflow-hidden"
      active={data.isActive}
      dimmed={data.isDimmed}
      highlighted={data.isHighlighted || selected}
      kindBorder={kindMeta?.border}
      kindGlow={kindMeta?.glow}
    >
      <Handle type="target" position={Position.Left} className="!w-2.5 !h-2.5" />
      <Handle type="source" position={Position.Right} className="!w-2.5 !h-2.5" />

      <div
        className={`relative bg-gradient-to-br ${reuseGradient}`}
        style={kindMeta ? { background: kindMeta.nodeBg } : undefined}
      >
        <KindNodeChrome
          kind={effectiveKind}
          roleLabel={
            data.branchLabel ? (
              <span className="text-[10px] font-semibold uppercase tracking-wide text-cyan-300">
                {data.branchLabel}
              </span>
            ) : undefined
          }
        >
          <div className="flex items-start justify-between gap-2">
            <p className="text-[15px] font-bold text-white leading-snug line-clamp-2 flex-1">
              {data.label}
            </p>
            <div className="flex flex-col items-end gap-1 shrink-0">
              <ReuseBadge reuse={data.reuse} />
              <StatusDot status={data.runtime.status} />
            </div>
          </div>

          {data.runtime.catalog ? (
            <p className="mt-1.5 text-[10px] text-slate-300 truncate max-w-[220px]">
              📦 {data.runtime.catalog}
            </p>
          ) : null}

          <MetricChips runtime={data.runtime} />

          <AnimatePresence>
            {data.expanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="mt-2 space-y-1 border-t border-white/15 pt-2 text-[10px] text-slate-300">
                  <p>
                    <span className="font-semibold text-white/70">
                      {data.implementationKind === "agent" ? "Sub-agents:" : "Components:"}
                    </span>{" "}
                    {data.runtime.tools.join(", ")}
                  </p>
                  {data.runtime.inputJson && (
                    <pre className="whitespace-pre-wrap break-all text-[9px] text-slate-400">
                      <span className="text-slate-500">In:</span>{" "}
                      {JSON.stringify(data.runtime.inputJson, null, 2)}
                    </pre>
                  )}
                  {data.runtime.outputJson && (
                    <pre className="whitespace-pre-wrap break-all text-[9px] text-slate-400">
                      <span className="text-slate-500">Out:</span>{" "}
                      {JSON.stringify(data.runtime.outputJson, null, 2)}
                    </pre>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </KindNodeChrome>
      </div>
    </NodeShell>
  );
}

function inferBuildKind(data: FlowNodeData): "agent" | "function" | "tool" | undefined {
  if (data.reuse) return undefined;
  const blob = `${data.label} ${data.description ?? ""}`.toLowerCase();
  if (/\b(blob|storage)\b/.test(blob)) return "tool";
  if (/\b(extract|reason|score|classif|generat)\b/.test(blob)) return "agent";
  return "agent";
}
