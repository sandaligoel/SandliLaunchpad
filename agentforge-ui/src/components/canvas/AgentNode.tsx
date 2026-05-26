import { Handle, Position, type NodeProps } from "@xyflow/react";
import { Database, Table, ShieldCheck, Wand2, GitBranch, Wrench, Brain, Globe, UploadCloud, Sparkles, AlertTriangle, CheckCircle2, Circle } from "lucide-react";
import type { AgentNodeData } from "@/store/workflowStore";
import { AGENT_REGISTRY } from "@/mocks/data";
import type { AgentType } from "@/types/api";

const ICONS = { Database, Table, ShieldCheck, Wand2, GitBranch, Wrench, Brain, Globe, UploadCloud, Sparkles } as const;

const STATUS_ICON = {
  valid: <CheckCircle2 size={12} className="text-[color:var(--color-success)]" />,
  warning: <AlertTriangle size={12} className="text-[color:var(--color-warning)]" />,
  error: <AlertTriangle size={12} className="text-[color:var(--color-danger)]" />,
  idle: <Circle size={12} className="text-muted-foreground" />,
};

export function AgentNodeView({ data, selected }: NodeProps<{ data: AgentNodeData; type: "agent"; position: { x: number; y: number }; id: string }>) {
  const def = AGENT_REGISTRY.find((a) => a.type === (data.agent as AgentType))!;
  const Icon = ICONS[def.icon as keyof typeof ICONS] ?? Wrench;
  return (
    <div
      className={`rounded-xl bg-surface border ${selected ? "border-primary shadow-lg" : "border-border"} min-w-[200px] overflow-hidden`}
    >
      <div className="flex items-center gap-2 px-3 py-2" style={{ background: def.color, color: "white" }}>
        <Icon size={14} />
        <span className="text-[12px] font-semibold flex-1 truncate">{data.label}</span>
        {STATUS_ICON[data.status ?? "idle"]}
      </div>
      <div className="px-3 py-2 text-[11px] text-muted-foreground">
        <div className="flex justify-between">
          <span className="uppercase tracking-wider">{def.type}</span>
          <span>{def.outputs.length} out</span>
        </div>
      </div>
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
