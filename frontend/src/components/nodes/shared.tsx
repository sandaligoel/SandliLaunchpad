import { motion } from "framer-motion";
import type { FlowNodeData, ReuseDecision } from "@/types/plan";

export function StatusDot({ status }: { status: FlowNodeData["runtime"]["status"] }) {
  const colors: Record<string, string> = {
    idle: "bg-slate-500",
    running: "bg-blue-400 animate-pulse",
    success: "bg-emerald-400",
    failed: "bg-red-400",
    skipped: "bg-slate-600",
  };
  return <span className={`h-2 w-2 rounded-full ${colors[status]}`} />;
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
  return (
    <div className="mt-2 flex flex-wrap gap-1">
      <span className="rounded bg-white/5 px-1.5 py-0.5 font-mono text-[10px] text-slate-400">
        {runtime.latencyMs}ms
      </span>
      {runtime.retries > 0 && (
        <span className="rounded bg-orange-500/15 px-1.5 py-0.5 text-[10px] text-orange-300">
          retry ×{runtime.retries}
        </span>
      )}
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

export function NodeShell({
  children,
  className = "",
  active,
  highlighted,
}: {
  children: React.ReactNode;
  className?: string;
  active?: boolean;
  highlighted?: boolean;
}) {
  return (
    <div
      className={`relative w-full max-w-[320px] rounded-xl border backdrop-blur-md transition-shadow ${className} ${
        active ? "shadow-glow border-blue-400/70" : highlighted ? "shadow-glow-green border-emerald-400/50" : ""
      }`}
    >
      <PulseRing active={active} />
      {children}
    </div>
  );
}
