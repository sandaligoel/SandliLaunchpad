import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import { AnimatePresence, motion } from "framer-motion";
import type { FlowNodeData } from "@/architecture-flow/types/plan";
import { MetricChips, NodeShell, ReuseBadge, StatusDot } from "@/architecture-flow/components/nodes/shared";

const STYLES: Record<string, string> = {
  "agent-reuse":
    "border-emerald-500/50 bg-gradient-to-br from-emerald-950/80 to-slate-900/90",
  "agent-adapt": "border-teal-500/50 bg-gradient-to-br from-teal-950/80 to-slate-900/90",
  "agent-build": "border-indigo-500/50 bg-gradient-to-br from-indigo-950/80 to-slate-900/90",
};

export function AgentNode({ data, selected }: NodeProps<Node<FlowNodeData>>) {
  const style = STYLES[data.kind] || STYLES["agent-build"];
  return (
    <NodeShell
      className={`${style} shadow-glass`}
      active={data.isActive}
      dimmed={data.isDimmed}
      highlighted={data.isHighlighted || selected}
      componentKind={data.componentKind ?? "agent"}
    >
      <Handle type="target" position={Position.Left} className="!w-2 !h-2" />
      <Handle type="source" position={Position.Right} className="!w-2 !h-2" />
      <div className="p-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            {data.branchLabel && (
              <span className="text-[10px] font-medium text-cyan-400">{data.branchLabel}</span>
            )}
            <p className="text-sm font-semibold text-white leading-snug line-clamp-2">
              {data.label}
            </p>
          </div>
          <div className="flex flex-col items-end gap-1">
            <ReuseBadge reuse={data.reuse} />
            <StatusDot status={data.runtime.status} />
          </div>
        </div>
        {(data.catalogAgentName || data.runtime.catalog) && data.componentKind === "agent" ? (
          <p className="mt-1 text-[10px] font-medium text-emerald-300/90 truncate max-w-[220px]">
            📦 {data.catalogAgentName || data.runtime.catalog}
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
              <div className="mt-2 space-y-1 border-t border-white/10 pt-2 text-[10px] text-slate-400">
                <p>
                  <span className="text-slate-500">Tools:</span> {data.runtime.tools.join(", ")}
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
      </div>
    </NodeShell>
  );
}
