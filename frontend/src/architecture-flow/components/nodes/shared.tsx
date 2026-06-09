import { motion } from "framer-motion";
import { Bot, Braces, Wrench } from "lucide-react";
import type { FlowNodeData, ImplementationKind, ReuseDecision } from "@/architecture-flow/types/plan";
import { KIND_META, kindBadgeStyle, type KindTone } from "@/utils/agentKind";

const KIND_ICONS = {
  agent: Bot,
  function: Braces,
  tool: Wrench,
} as const;

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

export function ImplementationKindBadge({
  kind,
  size = "md",
  tone = "canvas",
}: {
  kind?: ImplementationKind;
  size?: "sm" | "md" | "lg";
  tone?: KindTone;
}) {
  if (!kind) return null;
  const meta = KIND_META[kind];
  const Icon = KIND_ICONS[kind];
  const sizeClass =
    size === "lg"
      ? "px-3 py-1 text-[11px] gap-2 rounded-lg"
      : size === "sm"
        ? "px-1.5 py-0.5 text-[9px] gap-1 rounded"
        : "px-2.5 py-1 text-[10px] gap-1.5 rounded-md";
  const iconSize = size === "lg" ? 14 : size === "sm" ? 10 : 12;
  const styles = kindBadgeStyle(kind, tone);
  const glow =
    tone === "canvas" && size !== "sm" ? styles.boxShadow : undefined;
  return (
    <span
      className={`inline-flex items-center font-extrabold uppercase tracking-widest border ${size === "lg" ? "border-2" : ""} ${sizeClass}`}
      style={{
        color: styles.color,
        background: styles.background,
        borderColor: styles.borderColor,
        boxShadow: glow,
      }}
      title={`${meta.label} — multi-agent chain, LLM function, or infrastructure tool`}
    >
      <Icon size={iconSize} strokeWidth={2.5} aria-hidden />
      {meta.shortLabel}
    </span>
  );
}

export function ImplementationKindStripe({ kind }: { kind?: ImplementationKind }) {
  if (!kind) return null;
  const meta = KIND_META[kind];
  return (
    <div
      className="absolute inset-x-0 top-0 h-2.5 rounded-t-xl z-[1]"
      style={{
        background: `linear-gradient(90deg, ${meta.stripe}, ${meta.solid})`,
        boxShadow: `0 0 16px ${meta.glow}`,
      }}
      aria-hidden
    />
  );
}

export function ImplementationKindAccent({ kind }: { kind?: ImplementationKind }) {
  if (!kind) return null;
  const meta = KIND_META[kind];
  return (
    <div
      className="absolute left-0 top-0 bottom-0 w-[5px] rounded-l-xl z-[1]"
      style={{
        background: `linear-gradient(180deg, ${meta.stripe}, ${meta.solid})`,
        boxShadow: `0 0 18px ${meta.glow}`,
      }}
      aria-hidden
    />
  );
}

/** Shared type chrome for input, human, merge, and agent nodes. */
export function KindNodeChrome({
  kind,
  children,
  roleLabel,
}: {
  kind?: ImplementationKind;
  children: React.ReactNode;
  roleLabel?: React.ReactNode;
}) {
  const meta = kind ? KIND_META[kind] : null;
  return (
    <div
      className="relative overflow-hidden rounded-xl"
      style={meta ? { background: meta.nodeBg } : undefined}
    >
      {kind ? <ImplementationKindStripe kind={kind} /> : null}
      {kind ? <ImplementationKindAccent kind={kind} /> : null}
      <div className="relative px-3.5 pb-3.5 pl-5 pt-4">
        {kind || roleLabel ? (
          <div className="mb-2 flex flex-wrap items-center gap-2">
            {kind ? <ImplementationKindBadge kind={kind} size="lg" /> : null}
            {roleLabel}
          </div>
        ) : null}
        {children}
      </div>
    </div>
  );
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
  kindBorder,
  kindGlow,
}: {
  children: React.ReactNode;
  className?: string;
  active?: boolean;
  dimmed?: boolean;
  highlighted?: boolean;
  kindBorder?: string;
  kindGlow?: string;
}) {
  const kindStyle =
    kindBorder && !active && !dimmed
      ? {
          borderColor: kindBorder,
          borderWidth: 2,
          boxShadow: `0 0 0 1px ${kindBorder}, 0 0 24px ${kindGlow ?? kindBorder}`,
        }
      : undefined;

  return (
    <div
      className={`relative w-full max-w-[320px] rounded-xl border backdrop-blur-md transition-all duration-300 ${className} ${
        active
          ? "scale-[1.02] shadow-[0_0_28px_rgba(59,130,246,0.45)] border-blue-400 z-10"
          : dimmed
            ? "opacity-30 saturate-50 border-slate-700/50"
            : highlighted
              ? "shadow-glow-green border-emerald-400/50"
              : kindBorder
                ? ""
                : "border-slate-600/60"
      }`}
      style={kindStyle}
    >
      <PulseRing active={active} />
      {active && <RunningBanner />}
      {children}
    </div>
  );
}
