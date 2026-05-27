import type { SimulationState } from "@/hooks/useSimulation";

interface Props {
  state: SimulationState;
  onRun: () => void;
  onStop: () => void;
  disabled?: boolean;
}

export function SimulationPanel({ state, onRun, onStop, disabled }: Props) {
  const { simulating, stepIndex, stepTotal, currentStepLabel, progress } = state;
  const pct = stepTotal > 0 ? Math.round(progress * 100) : 0;

  return (
    <div
      className={`rounded-xl border p-3 transition-colors ${
        simulating
          ? "border-blue-500/50 bg-gradient-to-br from-blue-950/50 to-slate-900/80 shadow-[0_0_24px_rgba(59,130,246,0.15)]"
          : "border-border bg-panel/80"
      }`}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            className={`flex h-2 w-2 rounded-full ${
              simulating ? "bg-blue-400 animate-pulse shadow-[0_0_8px_#60a5fa]" : "bg-slate-600"
            }`}
            aria-hidden
          />
          <h3 className="text-xs font-bold uppercase tracking-widest text-slate-300">
            Walkthrough simulation
          </h3>
        </div>
        {simulating && (
          <span className="rounded-full bg-blue-500/25 px-2 py-0.5 text-[10px] font-semibold text-blue-200">
            LIVE
          </span>
        )}
      </div>

      <p className="mb-3 text-[11px] leading-relaxed text-slate-400">
        Watch work move through your diagram step by step. The active step glows blue; completed
        steps turn green; upcoming steps fade out.
      </p>

      {simulating && stepTotal > 0 && (
        <div className="mb-3 space-y-1.5">
          <div className="flex justify-between text-[10px] text-slate-500">
            <span>
              Step {stepIndex + 1} of {stepTotal}
            </span>
            <span>{pct}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-800/80">
            <div
              className="h-full rounded-full bg-gradient-to-r from-blue-500 to-cyan-400 transition-all duration-300 ease-out"
              style={{ width: `${Math.max(pct, simulating && stepIndex >= 0 ? 8 : 0)}%` }}
            />
          </div>
          {currentStepLabel && (
            <p className="text-xs font-medium text-blue-200">
              Now running: <span className="text-white">{currentStepLabel}</span>
            </p>
          )}
        </div>
      )}

      {!simulating && stepTotal > 0 && (
        <p className="mb-3 text-[10px] text-slate-500">
          {stepTotal} steps in this workflow
        </p>
      )}

      <div className="flex gap-2">
        <button
          type="button"
          onClick={onRun}
          disabled={disabled || simulating}
          className="flex-1 rounded-lg bg-blue-600 px-3 py-2 text-xs font-bold text-white shadow-lg shadow-blue-900/40 hover:bg-blue-500 disabled:opacity-40"
        >
          ▶ Play walkthrough
        </button>
        <button
          type="button"
          onClick={onStop}
          disabled={!simulating}
          className="rounded-lg border border-border bg-white/5 px-3 py-2 text-xs font-semibold text-slate-300 hover:bg-white/10 disabled:opacity-40"
        >
          Stop
        </button>
      </div>
    </div>
  );
}
