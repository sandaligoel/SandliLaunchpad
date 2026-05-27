import type { ArchitecturePlan } from "@/types/plan";
import type { SimulationState } from "@/hooks/useSimulation";

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
  simulationState?: SimulationState;
}

export function MetricsPanel({ plan, stats, simulating, stepIndex, simulationState }: Props) {
  if (!plan || !stats) {
    return (
      <div className="rounded-xl border border-border bg-panel/80 p-4 text-sm text-slate-500">
        Generate a plan to see pipeline metrics.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-4 gap-1.5">
        <MiniMetric label="Agents" value={String(stats.agents)} />
        <MiniMetric label="Parallel" value={String(stats.parallelBranches)} accent="cyan" />
        <MiniMetric label="Reuse" value={String(stats.reuse)} accent="green" />
        <MiniMetric label="Build" value={String(stats.build)} accent="indigo" />
      </div>
      {simulating && simulationState && simulationState.stepTotal > 0 && (
        <div className="rounded-lg border border-blue-500/30 bg-blue-500/10 px-2 py-1.5 text-xs text-blue-200">
          Step {stepIndex + 1} of {simulationState.stepTotal}
          {simulationState.currentStepLabel && (
            <span className="block text-[10px] text-blue-300/90 mt-0.5 truncate">
              {simulationState.currentStepLabel}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

function MiniMetric({
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
      className={`rounded-lg border border-border bg-gradient-to-br ${ring} to-transparent px-2 py-1.5`}
    >
      <p className="text-[9px] uppercase tracking-wide text-slate-500 leading-tight">{label}</p>
      <p className="text-sm font-semibold text-white leading-tight">{value}</p>
    </div>
  );
}
