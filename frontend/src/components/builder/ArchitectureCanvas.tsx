import { useCallback, useMemo } from "react";
import type { ArchitecturePlan } from "@/api/affine/types";
import type { AgentDef } from "@/types/api";
import { adaptGuruPlanToFlowPlan } from "@/architecture-flow/adaptLaunchpadPlan";
import { ArchitectureFlowView } from "@/architecture-flow/components/architecture/ArchitectureFlowView";
import { hydratePlanStepMetadata } from "@/utils/stepIo";
import { Maximize2 } from "lucide-react";
import { ImplementationKindLegend } from "@/components/shared/ImplementationKindLegend";

interface Props {
  plan: ArchitecturePlan;
  catalogAgents: AgentDef[];
}

export function ArchitectureCanvas({ plan, catalogAgents }: Props) {
  const hydrated = useMemo(
    () => hydratePlanStepMetadata(plan, catalogAgents),
    [plan, catalogAgents],
  );

  const flowPlan = useMemo(
    () => adaptGuruPlanToFlowPlan(hydrated, catalogAgents),
    [hydrated, catalogAgents],
  );

  const onFitToScreen = useCallback(() => {
    window.dispatchEvent(new CustomEvent("launchpad:fit-screen"));
  }, []);

  return (
    <div className="architecture-flow-scope flex-1 min-h-0 min-w-0 flex flex-col">
      <div className="flex shrink-0 items-center justify-between gap-3 border-b border-[#1e2a3a] bg-[#0f141c]/90 px-3 py-2.5">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">
            AI Workflow Graph
          </p>
          <p className="text-[10px] text-slate-500 mt-0.5">Flow → left to right</p>
        </div>
        <ImplementationKindLegend theme="dark" />
        <button
          type="button"
          onClick={onFitToScreen}
          className="inline-flex shrink-0 items-center gap-2 rounded-lg border border-blue-500/45 bg-blue-600/90 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-500"
          title="Show the entire workflow on full screen"
        >
          <Maximize2 size={14} aria-hidden />
          Fit to screen
        </button>
      </div>
      <div className="flex-1 min-h-0">
        <ArchitectureFlowView plan={flowPlan} builderShell />
      </div>
    </div>
  );
}
