import { createRoot, type Root } from "react-dom/client";
import type { ArchitecturePlan } from "@/types/plan";
import { ArchitectureFlowView } from "@/components/architecture/ArchitectureFlowView";

let root: Root | null = null;
let host: HTMLElement | null = null;

function render(el: HTMLElement, plan: ArchitecturePlan | null) {
  if (!root) {
    root = createRoot(el);
    host = el;
  }
  root.render(<ArchitectureFlowView plan={plan} onStats={updateSidebarStats} />);
}

function updateSidebarStats(
  stats: {
    agents: number;
    reuse: number;
    adapt: number;
    build: number;
    parallelBranches: number;
  } | null
) {
  if (!stats) return;
  window.dispatchEvent(
    new CustomEvent("launchpad:flow-stats", {
      detail: stats,
    })
  );
}

export function mount(el: HTMLElement, plan: ArchitecturePlan | null) {
  render(el, plan);
}

export function update(plan: ArchitecturePlan) {
  if (host && root) render(host, plan);
}

export function unmount() {
  root?.unmount();
  root = null;
  host = null;
}
