import { useMemo } from "react";
import type { ArchitecturePlan } from "@/api/affine/types";
import type { AgentDef } from "@/types/api";
import { adaptGuruPlanToFlowPlan } from "@/architecture-flow/adaptLaunchpadPlan";
import { ArchitectureFlowView } from "@/architecture-flow/components/architecture/ArchitectureFlowView";
import { hydratePlanStepMetadata } from "@/utils/stepIo";

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

  return (
    <div className="architecture-flow-scope flex-1 min-h-0 min-w-0 flex flex-col">
      <div className="flex shrink-0 items-center justify-between gap-2 border-b border-[#1e2a3a] bg-[#0f141c]/90 px-3 py-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">
            AI Workflow Graph
          </p>
          <p className="text-[10px] text-slate-500">
            Flow → left to right · click a step for details
          </p>
        </div>
      </div>
      <div className="flex-1 min-h-0">
        <ArchitectureFlowView plan={flowPlan} builderShell />
      </div>
    </div>
  );
}
