import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import { ArchitectureFlowView } from "@/components/architecture/ArchitectureFlowView";
import * as embed from "@/embed";
import type { ArchitecturePlan } from "@/types/plan";

declare global {
  interface Window {
    LaunchpadArchitecture?: {
      mount: (el: HTMLElement, plan: ArchitecturePlan | null) => void;
      update: (plan: ArchitecturePlan) => void;
      unmount: () => void;
      getNodeIo: (
        plan: ArchitecturePlan | null,
        nodeId: string
      ) => { inputJson: Record<string, unknown>; outputJson: Record<string, unknown> } | null;
    };
    __LAUNCHPAD_DEV_PLAN__?: ArchitecturePlan;
  }
}

window.LaunchpadArchitecture = {
  mount: embed.mount,
  update: embed.update,
  unmount: embed.unmount,
  getNodeIo: embed.getNodeIo,
};

const rootEl = document.getElementById("root");
if (rootEl) {
  const devPlan = window.__LAUNCHPAD_DEV_PLAN__;
  createRoot(rootEl).render(
    <StrictMode>
      <div className="h-screen w-screen">
        <ArchitectureFlowView plan={devPlan ?? null} />
      </div>
    </StrictMode>
  );
}
