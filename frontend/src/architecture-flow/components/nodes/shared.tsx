import { motion } from "framer-motion";
import type { FlowNodeData, ReuseDecision } from "@/architecture-flow/types/plan";
import {
  stepComponentKindLabel,
  type StepComponentKind,
} from "@/utils/stepComponentKind";

const FLOW_KIND_ACCENT: Record<StepComponentKind, string> = {
  agent: "border-l-emerald-400 shadow-[inset_4px_0_12px_rgba(16,185,129,0.25)]",
  tool: "border-l-sky-400 shadow-[inset_4px_0_12px_rgba(56,189,248,0.25)]",
  function: "border-l-violet-400 shadow-[inset_4px_0_12px_rgba(167,139,250,0.25)]",
};

export function FlowComponentKindRibbon({ kind }: { kind: StepComponentKind }) {
  const cls =
    kind === "agent"
      ? "flow-kind-ribbon flow-kind-ribbon--agent"
      : kind === "tool"
        ? "flow-kind-ribbon flow-kind-ribbon--tool"
        : "flow-kind-ribbon flow-kind-ribbon--function";
  return (
    <div className={cls} title={`${stepComponentKindLabel(kind)} step`}>
      <span className="flow-kind-ribbon__label">{stepComponentKindLabel(kind)}</span>
    </div>
  );
}

export function ComponentKindLegend() {
  const items: StepComponentKind[] = ["agent", "tool", "function"];
  return (
    <div className="flow-kind-legend" aria-label="Step component types">
      <span className="flow-kind-legend__title">Step type</span>
      {items.map((k) => (
        <span
          key={k}
          className={`flow-kind-legend__item flow-kind-legend__item--${k}`}
        >
          {stepComponentKindLabel(k)}
        </span>
      ))}
    </div>
  );
}

export function StatusDot({ status }: { status: FlowNodeData["runtime"]["status"] }) {
  const colors: Record<string, string> = {
    idle: "bg-slate-500",
    running: "bg-blue-400 animate-pulse shadow-[0_0_8px_#60a5fa]",
    success: "bg-emerald-400 shadow-[0_0_6px_#34d399]",
    failed: "bg-red-400",
    skipped: "bg-slate-600",
  };
  const ring =
    status === "running"
      ? "ring-2 ring-blue-400/50"
      : status === "success"
        ? "ring-2 ring-emerald-400/40"
        : "";
  return <span className={`h-2.5 w-2.5 rounded-full ${colors[status]} ${ring}`} />;
}

export function ReuseBadge({ reuse }: { reuse?: ReuseDecision }) {
  const map = {
    reuse: "REUSE",
    adapt: "ADAPT",
    build: "BUILD",
  } as const;
  const label = reuse ? map[reuse] : "BUILD";
  const cls =
    reuse === "reuse"
      ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
      : reuse === "adapt"
        ? "bg-teal-500/20 text-teal-300 border-teal-500/40"
        : "bg-indigo-500/20 text-indigo-300 border-indigo-500/40";
  return (
    <span className={`rounded border px-1.5 py-0.5 text-[10px] font-bold tracking-wide ${cls}`}>
      {label}
    </span>
  );
}

export function MetricChips({ runtime }: { runtime: FlowNodeData["runtime"] }) {
  if (!runtime.retries && !runtime.latencyMs) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-1">
      {runtime.latencyMs > 0 ? (
        <span className="rounded bg-slate-500/15 px-1.5 py-0.5 text-[10px] text-slate-400">
          {runtime.latencyMs}ms
        </span>
      ) : null}
      {runtime.retries ? (
        <span className="rounded bg-orange-500/15 px-1.5 py-0.5 text-[10px] text-orange-300">
          retry ×{runtime.retries}
        </span>
      ) : null}
    </div>
  );
}

export function PulseRing({ active }: { active?: boolean }) {
  if (!active) return null;
  return (
    <motion.span
      className="pointer-events-none absolute inset-0 rounded-xl border-2 border-blue-400/60"
      initial={{ opacity: 0.8, scale: 1 }}
      animate={{ opacity: 0, scale: 1.12 }}
      transition={{ duration: 1.4, repeat: Infinity }}
    />
  );
}

export function RunningBanner({ label }: { label?: string }) {
  return (
    <div className="absolute -top-2.5 left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded-full border border-blue-400/60 bg-blue-600 px-2.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-white shadow-[0_0_12px_rgba(59,130,246,0.6)]">
      ▶ {label || "Running"}
    </div>
  );
}

export function NodeShell({
  children,
  className = "",
  active,
  dimmed,
  highlighted,
  componentKind,
}: {
  children: React.ReactNode;
  className?: string;
  active?: boolean;
  dimmed?: boolean;
  highlighted?: boolean;
  componentKind?: StepComponentKind;
}) {
  const kindAccent = componentKind ? `border-l-[5px] ${FLOW_KIND_ACCENT[componentKind]}` : "";
  return (
    <div
      className={`relative w-full max-w-[320px] overflow-hidden rounded-xl border backdrop-blur-md transition-all duration-300 ${kindAccent} ${className} ${
        active
          ? "scale-[1.02] shadow-[0_0_28px_rgba(59,130,246,0.45)] border-blue-400 z-10"
          : dimmed
            ? "opacity-30 saturate-50 border-slate-700/50"
            : highlighted
              ? "shadow-glow-green border-emerald-400/50"
              : ""
      }`}
    >
      {componentKind ? <FlowComponentKindRibbon kind={componentKind} /> : null}
      <PulseRing active={active} />
      {active && <RunningBanner />}
      {children}
    </div>
  );
}
