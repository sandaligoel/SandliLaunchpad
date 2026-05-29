import { createRoot, type Root } from "react-dom/client";
import type { ArchitecturePlan, GraphNode } from "@/types/plan";
import { ArchitectureFlowView } from "@/components/architecture/ArchitectureFlowView";
import { buildNodeIoPayload } from "@/lib/mockRuntime";

let root: Root | null = null;
let host: HTMLElement | null = null;

function render(el: HTMLElement, plan: ArchitecturePlan | null) {
  if (!root) {
    root = createRoot(el);
    host = el;
  }
  const builderShell =
    el.dataset.builderShell === "1" ||
    (typeof document !== "undefined" &&
      document.getElementById("workspace")?.classList.contains("builder-layout") === true);
  root.render(<ArchitectureFlowView plan={plan} builderShell={builderShell} />);
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

export function getNodeIo(plan: ArchitecturePlan | null, nodeId: string) {
  if (!plan?.nodes?.length || !nodeId) return null;
  const node = plan.nodes.find((n) => n.id === nodeId);
  if (!node) return null;
  const { inputJson, outputJson } = buildNodeIoPayload(node as GraphNode, plan);
  return { inputJson, outputJson };
}
