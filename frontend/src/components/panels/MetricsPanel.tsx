import type { ArchitecturePlan } from "@/types/plan";

interface Props {
  plan: ArchitecturePlan | null;
  stats: {
    agents: number;
    reuse: number;
    adapt: number;
    build: number;
    parallelBranches: number;
  } | null;
  simulating: boolean;
  stepIndex: number;
}

export function MetricsPanel({ plan, stats, simulating, stepIndex }: Props) {
  if (!plan || !stats) {
    return (
      <div className="rounded-xl border border-border bg-panel/80 p-4 text-sm text-slate-500">
        Generate a plan to see pipeline metrics.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <MetricCard label="Agents" value={String(stats.agents)} />
        <MetricCard label="Parallel" value={String(stats.parallelBranches)} accent="cyan" />
        <MetricCard label="Reuse" value={String(stats.reuse)} accent="green" />
        <MetricCard label="Build" value={String(stats.build)} accent="indigo" />
      </div>
      {simulating && (
        <p className="text-xs text-blue-400 animate-pulse">
          Simulating step {stepIndex + 1}…
        </p>
      )}
      {plan.narrative && (
        <p className="text-xs leading-relaxed text-slate-400 line-clamp-4">{plan.narrative}</p>
      )}
    </div>
  );
}

function MetricCard({
  label,
  value,
  accent = "blue",
}: {
  label: string;
  value: string;
  accent?: string;
}) {
  const ring =
    accent === "green"
      ? "from-emerald-500/20"
      : accent === "cyan"
        ? "from-cyan-500/20"
        : accent === "indigo"
          ? "from-indigo-500/20"
          : "from-blue-500/20";
  return (
    <div
      className={`rounded-lg border border-border bg-gradient-to-br ${ring} to-transparent px-3 py-2`}
    >
      <p className="text-[10px] uppercase tracking-wide text-slate-500">{label}</p>
      <p className="text-lg font-semibold text-white">{value}</p>
    </div>
  );
}
