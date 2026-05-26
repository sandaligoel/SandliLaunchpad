import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { ArchitectureNodeData } from "@/utils/graphLayout";

const TYPE_ICON: Record<string, string> = {
  gateway: "⬡",
  agent: "◆",
  human: "◎",
  custom: "＋",
};

function LaunchpadPlanNode({ data, selected }: NodeProps) {
  const d = data as ArchitectureNodeData;
  const decision = d.decision ?? "build";
  const isSelected = selected || d.selected;
  const borderClass =
    decision === "reuse"
      ? "border-[color:var(--color-success)]"
      : decision === "adapt"
        ? "border-[#63b3ed]"
        : "border-muted-foreground/40";

  return (
    <div
      className={`min-w-[200px] max-w-[240px] rounded-xl border-2 bg-card px-3 py-2.5 shadow-md transition-shadow ${borderClass} ${isSelected ? "ring-2 ring-primary shadow-lg" : ""}`}
    >
      <Handle type="target" position={Position.Left} className="!w-2.5 !h-2.5 !bg-primary" />
      <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground uppercase tracking-wide mb-1">
        {d.layer != null ? <span>Step {d.layer}</span> : null}
        <span>{TYPE_ICON[d.nodeType] ?? "•"}</span>
        <span>{d.nodeType}</span>
      </div>
      <div className="text-sm font-semibold leading-snug">{d.label}</div>
      {d.agentName ? (
        <div className="text-xs text-primary mt-0.5 truncate">{d.agentName}</div>
      ) : null}
      <div className="flex flex-wrap gap-1 mt-2">
        <span
          className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${
            decision === "reuse"
              ? "bg-[color:var(--color-success)]/15 text-[color:var(--color-success)]"
              : decision === "adapt"
                ? "bg-sky-500/15 text-sky-600"
                : "bg-muted text-muted-foreground"
          }`}
        >
          {decision === "reuse"
            ? "Reuse catalog"
            : decision === "adapt"
              ? "Adapt catalog"
              : "Build new"}
        </span>
      </div>
      <Handle type="source" position={Position.Right} className="!w-2.5 !h-2.5 !bg-primary" />
    </div>
  );
}

export default memo(LaunchpadPlanNode);
