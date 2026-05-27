import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import { AnimatePresence, motion } from "framer-motion";
import type { FlowNodeData } from "@/types/plan";
import { MetricChips, NodeShell, ReuseBadge, StatusDot } from "@/components/nodes/shared";

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
        {data.runtime.catalog && (
          <p className="mt-1 text-[10px] text-slate-400 truncate max-w-[200px]">
            📦 {data.runtime.catalog}
          </p>
        )}
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
                <p>
                  <span className="text-slate-500">In:</span> {data.runtime.inputs.join(", ")}
                </p>
                <p>
                  <span className="text-slate-500">Out:</span> {data.runtime.outputs.join(", ")}
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </NodeShell>
  );
}
