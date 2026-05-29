import type { SimulationState } from "@/hooks/useSimulation";

interface Props {
  state: SimulationState;
  onRun: () => void;
  onStop: () => void;
  disabled?: boolean;
}

export function SimulationPanel({ state, onRun, onStop, disabled }: Props) {
  const { simulating } = state;

  return (
    <div className="flex flex-col gap-1.5">
      <button
        type="button"
        onClick={onRun}
        disabled={disabled || simulating}
        className="w-full rounded-md bg-blue-600 px-2 py-2 text-[11px] font-bold text-white hover:bg-blue-500 disabled:opacity-40"
        title="Play walkthrough"
      >
        ▶ Start
      </button>
      <button
        type="button"
        onClick={onStop}
        disabled={!simulating}
        className="w-full rounded-md border border-border bg-white/5 px-2 py-2 text-[11px] font-semibold text-slate-300 hover:bg-white/10 disabled:opacity-40"
        title="Stop walkthrough"
      >
        Stop
      </button>
    </div>
  );
}
