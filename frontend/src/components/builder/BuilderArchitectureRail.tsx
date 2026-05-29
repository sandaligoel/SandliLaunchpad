import { useCallback, useEffect, useState } from "react";
import type { ArchitecturePlan } from "@/api/affine/types";
import type { AgentDef } from "@/types/api";
import { countReuseStats } from "@/architecture-flow/lib/planReuse";
import { adaptGuruPlanToFlowPlan } from "@/architecture-flow/adaptLaunchpadPlan";
import {
  StepDetailInspector,
  type StepDetailPayload,
} from "@/components/builder/StepDetailInspector";

interface Props {
  plan: ArchitecturePlan;
  catalogAgents: AgentDef[];
}

export function BuilderArchitectureRail({ plan, catalogAgents }: Props) {
  const [detail, setDetail] = useState<StepDetailPayload | null>(null);
  const [simStep, setSimStep] = useState({ index: 0, total: 0, label: "" });

  const flowPlan = adaptGuruPlanToFlowPlan(plan, catalogAgents);
  const stats = countReuseStats(flowPlan);
  const parallel =
    flowPlan.edges.filter((e) => e.label === "branch").length > 0 ? 1 : 0;

  useEffect(() => {
    const onDetail = (e: Event) => {
      const d = (e as CustomEvent<StepDetailPayload>).detail;
      if (d?.id) setDetail(d);
    };
    const onClear = () => setDetail(null);
    const onSim = (e: Event) => {
      const d = (
        e as CustomEvent<{ stepIndex: number; stepTotal: number; label: string }>
      ).detail;
      if (d) setSimStep({ index: d.stepIndex, total: d.stepTotal, label: d.label });
    };
    window.addEventListener("launchpad:node-detail", onDetail);
    window.addEventListener("launchpad:clear-step", onClear);
    window.addEventListener("launchpad:simulation-step", onSim);
    return () => {
      window.removeEventListener("launchpad:node-detail", onDetail);
      window.removeEventListener("launchpad:clear-step", onClear);
      window.removeEventListener("launchpad:simulation-step", onSim);
    };
  }, []);

  const runWalkthrough = useCallback(() => {
    window.dispatchEvent(new CustomEvent("launchpad:sim-run"));
  }, []);

  const stopWalkthrough = useCallback(() => {
    window.dispatchEvent(new CustomEvent("launchpad:sim-stop"));
  }, []);

  const agentCount = plan.graph.nodes.filter(
    (n) => n.type === "agent" || n.type === "custom" || n.type === "gateway",
  ).length;

  return (
    <div className="builder-inspector-column">
      <div className="builder-arch-rail-compact">
        <section className="builder-arch-rail__section">
          <h3 className="builder-arch-rail__title">Walkthrough</h3>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={runWalkthrough}
              className="flex-1 rounded-md bg-blue-600 px-2 py-1.5 text-[10px] font-bold text-white hover:bg-blue-500"
            >
              ▶ Play
            </button>
            <button
              type="button"
              onClick={stopWalkthrough}
              className="rounded-md border border-[#1e2a3a] px-2 py-1.5 text-[10px] text-slate-300 hover:bg-white/5"
            >
              Stop
            </button>
          </div>
          {simStep.total > 0 ? (
            <p className="text-[10px] text-blue-300 mt-1.5 m-0">
              {Math.min(simStep.index + 1, simStep.total)} / {simStep.total}
              {simStep.label ? ` · ${simStep.label}` : ""}
            </p>
          ) : null}
        </section>
        <section className="builder-arch-rail__section !py-2">
          <div className="builder-arch-metrics">
            <span>
              <strong>{agentCount || stats.agents}</strong>
              Agents
            </span>
            <span>
              <strong>{parallel}</strong>
              Par
            </span>
            <span>
              <strong>{stats.reuse + stats.adapt}</strong>
              Reuse
            </span>
            <span>
              <strong>{stats.build}</strong>
              Build
            </span>
          </div>
        </section>
      </div>
      <StepDetailInspector detail={detail} />
    </div>
  );
}
