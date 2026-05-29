import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import { motion } from "framer-motion";
import type { FlowNodeData } from "@/types/plan";
import { NodeShell, StatusDot } from "@/components/nodes/shared";

export function OrchestratorNode({ data, selected }: NodeProps<Node<FlowNodeData>>) {
  return (
    <NodeShell
      className="border-accent/60 bg-gradient-to-br from-blue-950/90 via-indigo-900/80 to-blue-950/90 shadow-glass"
      active={data.isActive}
      dimmed={data.isDimmed}
      highlighted={data.isHighlighted || selected}
    >
      <Handle type="target" position={Position.Left} className="!bg-blue-400 !w-2 !h-2" />
      <Handle type="source" position={Position.Right} className="!bg-blue-400 !w-2 !h-2" />
      <div className="p-3">
        <div className="flex items-center gap-2">
          <motion.div
            className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/30 text-lg"
            animate={data.isActive ? { scale: [1, 1.08, 1] } : {}}
            transition={{ repeat: Infinity, duration: 1.6 }}
          >
            🧠
          </motion.div>
          <div className="flex-1">
            <span className="text-[10px] font-bold tracking-widest text-blue-300">ORCHESTRATOR</span>
            <p className="text-sm font-semibold text-white">{data.label}</p>
          </div>
          <StatusDot status={data.runtime.status} />
        </div>
        {data.description && (
          <p
            className={`mt-2 text-[11px] text-blue-200/70 ${
              data.expanded ? "line-clamp-none" : "line-clamp-2"
            }`}
          >
            {data.description}
          </p>
        )}
      </div>
    </NodeShell>
  );
}
