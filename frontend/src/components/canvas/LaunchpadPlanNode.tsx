import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { Bot, GitBranch, Plus, UserRound } from "lucide-react";
import type { ArchitectureNodeData } from "@/utils/graphLayout";
import { NODE_WIDTH } from "@/utils/graphLayout";
import { nodeTypeTheme } from "@/utils/workflowTheme";

const TYPE_META: Record<
  string,
  { icon: typeof Bot; label: string }
> = {
  gateway: { icon: GitBranch, label: "Gateway" },
  agent: { icon: Bot, label: "Agent" },
  human: { icon: UserRound, label: "Human" },
  custom: { icon: Plus, label: "Step" },
};

function LaunchpadPlanNode({ data, selected }: NodeProps) {
  const d = data as ArchitectureNodeData;
  const decision = d.decision ?? "build";
  const isSelected = selected || d.selected;
  const typeKey = d.nodeType in TYPE_META ? d.nodeType : "custom";
  const meta = TYPE_META[typeKey] ?? TYPE_META.custom;
  const Icon = meta.icon;
  const accent = nodeTypeTheme(typeKey);

  const decisionStyles =
    decision === "reuse"
      ? "border-emerald-500/50 bg-emerald-50/40"
      : decision === "adapt"
        ? "border-sky-500/45 bg-sky-50/40"
        : "border-slate-200/90 bg-white/95";

  return (
    <div
      className={`launchpad-plan-node group relative rounded-2xl border bg-white/95 backdrop-blur-sm transition-all duration-200 ${decisionStyles} ${
        isSelected
          ? "ring-2 ring-indigo-500/80 shadow-xl shadow-indigo-500/15 z-10 scale-[1.02]"
          : "shadow-md shadow-slate-900/8 hover:shadow-lg z-[1]"
      }`}
      style={{ width: NODE_WIDTH }}
    >
      <div
        className="absolute inset-y-3 left-0 w-1 rounded-full"
        style={{ background: accent.accent }}
        aria-hidden
      />
      <div
        className="absolute inset-0 rounded-2xl opacity-60 pointer-events-none"
        style={{
          background: `linear-gradient(135deg, ${accent.soft} 0%, transparent 55%)`,
        }}
        aria-hidden
      />

      <Handle
        type="target"
        position={Position.Left}
        id="in"
        isConnectable
        className="launchpad-flow-handle launchpad-flow-handle--in"
      />

      <div className="relative px-4 pt-3.5 pb-3.5 pl-5 min-w-0">
        <div className="flex items-start gap-2 mb-2">
          <span
            className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg mt-0.5"
            style={{
              background: accent.soft,
              color: accent.accent,
            }}
          >
            <Icon className="h-3.5 w-3.5" strokeWidth={2.25} />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              {d.layer != null ? (
                <span className="text-indigo-600">Step {d.layer}</span>
              ) : null}
              {d.layer != null ? (
                <span className="text-slate-400" aria-hidden>
                  ·
                </span>
              ) : null}
              <span>{meta.label}</span>
            </div>
          </div>
        </div>

        <h3
          className="text-[13px] font-semibold leading-snug text-slate-900 break-words"
          title={d.label}
        >
          {d.label}
        </h3>

        {d.agentName ? (
          <p
            className="text-xs text-indigo-700 mt-2 font-medium leading-relaxed break-words"
            title={d.agentName}
          >
            {d.agentName}
          </p>
        ) : null}

        {d.description ? (
          <p
            className="text-[11px] text-slate-600 mt-2 leading-relaxed break-words whitespace-normal"
            title={d.description}
          >
            {d.description}
          </p>
        ) : null}

        {d.rationale ? (
          <p
            className="text-[10px] text-slate-500 mt-2 leading-relaxed break-words whitespace-normal italic"
            title={d.rationale}
          >
            {d.rationale}
          </p>
        ) : null}

        <div className="mt-3 pt-2.5 border-t border-slate-100">
          <span
            className={`inline-flex max-w-full text-[10px] font-bold uppercase tracking-wide px-2.5 py-1 rounded-full break-words whitespace-normal text-center ${
              decision === "reuse"
                ? "bg-emerald-100 text-emerald-800"
                : decision === "adapt"
                  ? "bg-sky-100 text-sky-800"
                  : "bg-slate-100 text-slate-600"
            }`}
          >
            {decision === "reuse"
              ? "Reuse catalog"
              : decision === "adapt"
                ? "Adapt catalog"
                : "Build new"}
          </span>
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        id="out"
        isConnectable
        className="launchpad-flow-handle launchpad-flow-handle--out"
      />
    </div>
  );
}

export default memo(LaunchpadPlanNode);
