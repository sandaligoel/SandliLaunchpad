import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";

export type ArchitectureNodeData = {
  label: string;
  nodeType: string;
  decision: string;
  agentId?: string | null;
  agentName?: string | null;
  rationale?: string;
  description?: string | null;
  layer?: number;
  selected?: boolean;
  validationLevel?: "pass" | "warn" | "fail";
};

const TYPE_ICON: Record<string, string> = {
  gateway: "⬡",
  agent: "◆",
  human: "◎",
  custom: "＋",
};

function ArchitectureNode({ data, selected }: NodeProps) {
  const d = data as ArchitectureNodeData;
  const decision = d.decision ?? "build";
  const isSelected = selected || d.selected;
  const icon = TYPE_ICON[d.nodeType] ?? "•";
  const vLevel = d.validationLevel;
  const vClass =
    vLevel && vLevel !== "pass" ? `arch-node--val-${vLevel}` : "";

  return (
    <div
      className={`arch-node arch-node--${d.nodeType} arch-node--${decision} ${isSelected ? "arch-node--selected" : ""} ${vClass}`}
    >
      <Handle type="target" position={Position.Left} className="arch-node__handle" />
      <div className="arch-node__head">
        {d.layer != null ? (
          <span className="arch-node__step">Step {d.layer}</span>
        ) : null}
        <span className="arch-node__icon" aria-hidden>
          {icon}
        </span>
        <span className="arch-node__type">{d.nodeType}</span>
      </div>
      <strong className="arch-node__label">{d.label}</strong>
      {d.agentName ? (
        <span className="arch-node__agent" title={d.agentId ?? undefined}>
          {d.agentName}
        </span>
      ) : d.agentId ? (
        <span className="arch-node__agent mono">{d.agentId}</span>
      ) : null}
      <div className="arch-node__badges">
        <span className={`arch-node__badge arch-node__badge--${decision}`}>
          {decision}
        </span>
        {vLevel && vLevel !== "pass" ? (
          <span className={`arch-node__badge arch-node__badge--val-${vLevel}`}>
            {vLevel === "fail" ? "fix" : "review"}
          </span>
        ) : null}
      </div>
      <Handle type="source" position={Position.Right} className="arch-node__handle" />
    </div>
  );
}

export default memo(ArchitectureNode);
