import { useCallback, useEffect, useMemo, useState } from "react";
import { DEBUG_LAYOUT } from "@/architecture-flow/layout/constants";
import { LayoutDebugOverlay } from "@/architecture-flow/components/layout/LayoutDebugOverlay";
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  Panel,
  ReactFlow,
  ReactFlowProvider,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import type { ArchitecturePlan, FlowNodeData } from "@/architecture-flow/types/plan";
import {
  findReuseDecisionForNode,
  resolveCatalogConfidence,
} from "@/architecture-flow/lib/planReuse";
import { resolveStepComponentKind } from "@/utils/stepComponentKind";
import { useSimulation } from "@/architecture-flow/hooks/useSimulation";
import { useGraphViewport } from "@/architecture-flow/hooks/useGraphViewport";
import {
  defaultFitViewOptions,
  fullscreenFitViewOptions,
} from "@/architecture-flow/layout/viewport";
import { Maximize2 } from "lucide-react";
import { AnimatedEdge } from "@/architecture-flow/components/edges/AnimatedEdge";
import { InputNode } from "@/architecture-flow/components/nodes/InputNode";
import { OrchestratorNode } from "@/architecture-flow/components/nodes/OrchestratorNode";
import { AgentNode } from "@/architecture-flow/components/nodes/AgentNode";
import { MergeNode } from "@/architecture-flow/components/nodes/MergeNode";
import { HumanNode } from "@/architecture-flow/components/nodes/HumanNode";
import { ParallelGroupNode } from "@/architecture-flow/components/nodes/ParallelGroupNode";
import { LaneLabelNode } from "@/architecture-flow/components/nodes/LaneLabelNode";
import { LaneBandNode } from "@/architecture-flow/components/nodes/LaneBandNode";
import { SimulationPanel } from "@/architecture-flow/components/panels/SimulationPanel";
import { ComponentKindLegend } from "@/architecture-flow/components/nodes/shared";

const nodeTypes = {
  input: InputNode,
  orchestrator: OrchestratorNode,
  "agent-reuse": AgentNode,
  "agent-adapt": AgentNode,
  "agent-build": AgentNode,
  merge: MergeNode,
  decision: MergeNode,
  human: HumanNode,
  parallelGroup: ParallelGroupNode,
  laneLabel: LaneLabelNode,
  laneBand: LaneBandNode,
};

const edgeTypes = { animated: AnimatedEdge };

function SimulationCanvasBanner({
  simulating,
  stepIndex,
  stepTotal,
  currentStepLabel,
  stepDurationMs,
}: {
  simulating: boolean;
  stepIndex: number;
  stepTotal: number;
  currentStepLabel: string;
  stepDurationMs: number;
}) {
  if (!simulating || stepTotal === 0) return null;
  return (
    <div className="pointer-events-none flex items-center gap-3 rounded-lg border border-blue-500/50 bg-blue-950/90 px-4 py-2 shadow-[0_8px_32px_rgba(59,130,246,0.35)] backdrop-blur-md">
      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-500/30 text-lg animate-pulse">
        ▶
      </span>
      <div>
        <p className="text-[10px] font-bold uppercase tracking-widest text-blue-300">
          Simulation in progress
        </p>
        <p className="text-sm font-semibold text-white">
          Step {Math.min(stepIndex + 1, stepTotal)} / {stepTotal}
          {currentStepLabel ? ` — ${currentStepLabel}` : ""}
        </p>
        <p className="text-[10px] text-blue-200/90">
          {Math.round(stepDurationMs / 1000)}s per step
        </p>
      </div>
    </div>
  );
}

function FlowInner({
  plan,
  builderShell = false,
}: {
  plan: ArchitecturePlan | null;
  builderShell?: boolean;
}) {
  const {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    simulating,
    stepIndex,
    simulationState,
    run,
    stop,
    toggleExpand,
    selectNode,
    layoutLoading,
    layoutMeta,
    currentStepId,
  } = useSimulation(plan);

  const { translateExtent, applyFit, applyFullscreenFit, focusNode, viewportConfig } =
    useGraphViewport(nodes, layoutLoading, layoutMeta);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [layoutDebug, setLayoutDebug] = useState(DEBUG_LAYOUT);
  const [fullscreen, setFullscreen] = useState(false);

  const fitToScreen = useCallback(async () => {
    if (simulating) stop();
    setFullscreen(true);
    document.body.classList.add("launchpad-arch-fullscreen");
    await new Promise<void>((resolve) => {
      requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
    });
    await applyFullscreenFit();
  }, [applyFullscreenFit, simulating, stop]);

  const exitFullscreen = useCallback(() => {
    setFullscreen(false);
    document.body.classList.remove("launchpad-arch-fullscreen");
    requestAnimationFrame(() => {
      void applyFit("full");
    });
  }, [applyFit]);

  useEffect(() => {
    if (!fullscreen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") exitFullscreen();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [fullscreen, exitFullscreen]);

  useEffect(() => {
    return () => {
      document.body.classList.remove("launchpad-arch-fullscreen");
    };
  }, []);

  useEffect(() => {
    if (!builderShell) return;
    const onRun = () => run();
    const onStop = () => stop();
    const onFitScreen = () => void fitToScreen();
    window.addEventListener("launchpad:sim-run", onRun);
    window.addEventListener("launchpad:sim-stop", onStop);
    window.addEventListener("launchpad:fit-screen", onFitScreen);
    return () => {
      window.removeEventListener("launchpad:sim-run", onRun);
      window.removeEventListener("launchpad:sim-stop", onStop);
      window.removeEventListener("launchpad:fit-screen", onFitScreen);
    };
  }, [builderShell, run, stop, fitToScreen]);

  useEffect(() => {
    if (!fullscreen) return;
    let t: ReturnType<typeof setTimeout>;
    const onResize = () => {
      clearTimeout(t);
      t = setTimeout(() => void applyFullscreenFit(), 200);
    };
    window.addEventListener("resize", onResize);
    return () => {
      clearTimeout(t);
      window.removeEventListener("resize", onResize);
    };
  }, [fullscreen, applyFullscreenFit]);

  useEffect(() => {
    if (simulating && currentStepId) {
      const t = window.setTimeout(() => focusNode(currentStepId), 80);
      return () => window.clearTimeout(t);
    }
  }, [simulating, currentStepId, focusNode]);

  const emitBuilderNodeDetail = useCallback(
    (node: Node<FlowNodeData>) => {
      const inBuilder =
        builderShell ||
        (typeof document !== "undefined" &&
          document.getElementById("workspace")?.classList.contains("builder-layout"));
      if (!inBuilder) return;
      const graphNode = plan?.nodes.find((n) => n.id === node.id);
      const confidence = graphNode ? resolveCatalogConfidence(plan, graphNode) : null;
      const reuseRow = graphNode ? findReuseDecisionForNode(plan, graphNode) : undefined;
      const reuse = node.data.reuse || graphNode?.reuse_decision || "build";
      const componentKind =
        node.data.componentKind ?? resolveStepComponentKind(graphNode, reuse);
      window.dispatchEvent(
        new CustomEvent("launchpad:node-detail", {
          detail: {
            id: node.id,
            label: node.data.label,
            description: node.data.description || "",
            reuse,
            confidence,
            componentKind,
            catalogAgentName:
              node.data.catalogAgentName ?? reuseRow?.agent_name ?? undefined,
            catalogRationale: reuseRow?.rationale,
            lane: node.data.lane,
            status: node.data.runtime.status,
            latencyMs: node.data.runtime.latencyMs,
            inputJson: node.data.runtime.inputJson,
            outputJson: node.data.runtime.outputJson,
            tools: node.data.runtime.tools,
            inputs: node.data.runtime.inputs,
            outputs: node.data.runtime.outputs,
            implementationKind: node.data.implementationKind,
          },
        })
      );
    },
    [builderShell, plan]
  );

  useEffect(() => {
    const handler = (e: Event) => {
      const id = (e as CustomEvent<{ nodeId: string }>).detail?.nodeId;
      if (id) {
        selectNode(id);
        setSelectedId(id);
        const n = nodes.find((x) => x.id === id);
        if (n) emitBuilderNodeDetail(n);
        focusNode(id);
      }
    };
    window.addEventListener("launchpad:select-node", handler);
    return () => window.removeEventListener("launchpad:select-node", handler);
  }, [nodes, selectNode, focusNode, emitBuilderNodeDetail]);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node<FlowNodeData>) => {
      if (node.id.startsWith("__lane_") || node.type === "laneBand") return;
      setSelectedId(node.id);
      selectNode(node.id);
      if (builderShell) emitBuilderNodeDetail(node);
      if (node.type?.toString().startsWith("agent") && !builderShell) {
        toggleExpand(node.id);
      }
    },
    [selectNode, toggleExpand, builderShell, emitBuilderNodeDetail]
  );

  const onPaneClick = useCallback(() => {
    setSelectedId(null);
    selectNode(null);
    if (
      builderShell ||
      document.getElementById("workspace")?.classList.contains("builder-layout")
    ) {
      window.dispatchEvent(new CustomEvent("launchpad:clear-step"));
    }
  }, [selectNode, builderShell]);

  const defaultEdgeOptions = useMemo(
    () => ({ type: "animated" as const, animated: true }),
    []
  );

  const graphSizeHint = layoutMeta
    ? `${Math.round(layoutMeta.bounds.width)}×${Math.round(layoutMeta.bounds.height)}px canvas · pan to explore`
    : "Pan · scroll to zoom";

  const canvasClass = simulating ? "launchpad-flow-canvas launchpad-flow-simulating" : "launchpad-flow-canvas";

  return (
    <div
      className={
        fullscreen
          ? "fixed inset-0 z-[500] flex flex-col bg-canvas pt-11"
          : "flex h-full min-h-0 flex-col"
      }
    >
      {!fullscreen && !builderShell && (
      <div className="arch-flow-toolbar flex flex-shrink-0 flex-wrap items-center justify-between gap-2 border-b border-border bg-panel/60 px-3 py-2 backdrop-blur-md">
        <div className="flex flex-col gap-0.5">
          <span className="text-xs font-semibold uppercase tracking-widest text-slate-400">
            AI Workflow Graph
          </span>
          <span className="text-[10px] text-slate-500">{graphSizeHint}</span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {layoutLoading && (
            <span className="rounded-full bg-slate-500/20 px-2 py-0.5 text-[10px] text-slate-400">
              Layout…
            </span>
          )}
          <button
            type="button"
            onClick={() => void fitToScreen()}
            className="inline-flex items-center gap-1.5 rounded-lg border border-blue-500/40 bg-blue-500/10 px-3 py-1.5 text-xs font-medium text-blue-100 hover:bg-blue-500/20"
            title="Show the entire workflow full screen"
          >
            <Maximize2 size={14} aria-hidden />
            Fit to screen
          </button>
          <button
            type="button"
            onClick={() => void applyFit("orchestrator")}
            className="rounded-lg border border-border bg-white/5 px-3 py-1.5 text-xs text-slate-300 hover:bg-white/10"
            title="Focus orchestration path"
          >
            Focus path
          </button>
          {selectedId && (
            <button
              type="button"
              onClick={() => focusNode(selectedId)}
              className="rounded-lg border border-blue-500/40 bg-blue-500/10 px-3 py-1.5 text-xs text-blue-200 hover:bg-blue-500/20"
            >
              Focus node
            </button>
          )}
          <button
            type="button"
            onClick={() => {
              const next = !layoutDebug;
              setLayoutDebug(next);
              try {
                localStorage.setItem("launchpad_layout_debug", next ? "1" : "0");
              } catch {
                /* ignore */
              }
            }}
            className={`rounded-lg border px-3 py-1.5 text-xs ${
              layoutDebug
                ? "border-amber-500/50 bg-amber-500/15 text-amber-200"
                : "border-border bg-white/5 text-slate-400"
            }`}
          >
            Layout debug
          </button>
        </div>
      </div>
      )}

      {fullscreen && (
        <div className="absolute left-0 right-0 top-0 z-[600] flex items-center justify-between gap-3 border-b border-white/10 bg-slate-950/90 px-4 py-2 backdrop-blur-md">
          <p className="text-xs text-slate-300">
            <span className="font-semibold text-white">Full screen</span>
            <span className="mx-2 text-slate-600">·</span>
            Entire workflow fitted to view
            <span className="mx-2 text-slate-600">·</span>
            <span className="text-slate-500">Esc to exit</span>
          </p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => void applyFullscreenFit()}
              className="inline-flex items-center gap-1.5 rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs text-slate-200 hover:bg-white/10"
            >
              <Maximize2 size={14} aria-hidden />
              Refit
            </button>
            <button
              type="button"
              onClick={exitFullscreen}
              className="rounded-lg border border-white/20 bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700"
            >
              Exit
            </button>
          </div>
        </div>
      )}

      <div className="flex min-h-0 min-w-0 flex-1">
        <div className={`${canvasClass} relative min-h-0 min-w-0 flex-1`}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            defaultEdgeOptions={defaultEdgeOptions}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            minZoom={viewportConfig.minZoom}
            maxZoom={viewportConfig.maxZoom}
            translateExtent={translateExtent}
            panOnDrag
            panOnScroll={false}
            zoomOnScroll
            zoomOnPinch
            zoomOnDoubleClick={false}
            preventScrolling={false}
            selectionOnDrag={false}
            nodesDraggable
            nodesConnectable={false}
            elementsSelectable
            onlyRenderVisibleElements
            elevateNodesOnSelect
            fitView={false}
            proOptions={{ hideAttribution: true }}
            className="launchpad-react-flow bg-canvas"
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={22}
              size={1}
              color={simulating ? "#1e3a5f" : "#1e293b"}
            />
            <LayoutDebugOverlay enabled={layoutDebug} />
            {!fullscreen && (
              <>
                <Panel position="top-center" className="!mt-3 !p-0">
                  <SimulationCanvasBanner
                    simulating={simulating}
                    stepIndex={stepIndex}
                    stepTotal={simulationState.stepTotal}
                    currentStepLabel={simulationState.currentStepLabel}
                    stepDurationMs={simulationState.stepDurationMs}
                  />
                </Panel>
                <Panel position="top-left" className="!m-2 !p-0 flex flex-col gap-2">
                  <ComponentKindLegend />
                  <div className="rounded-md border border-border/80 bg-panel/90 px-2 py-1 text-[10px] text-slate-500 backdrop-blur-sm">
                    {simulating ? (
                      <span className="text-blue-300">Simulation running — follow the blue glow</span>
                    ) : (
                      <>Drag to pan · Wheel / pinch to zoom</>
                    )}
                  </div>
                </Panel>
                {builderShell && (
                  <Panel position="top-right" className="!m-2 !p-0">
                    <button
                      type="button"
                      onClick={() => void fitToScreen()}
                      disabled={layoutLoading}
                      className="inline-flex items-center gap-2 rounded-lg border border-blue-500/50 bg-blue-600 px-3 py-2 text-xs font-semibold text-white shadow-lg shadow-blue-900/40 transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
                      title="Show the entire workflow on full screen"
                    >
                      <Maximize2 size={15} aria-hidden />
                      Fit to screen
                    </button>
                  </Panel>
                )}
              </>
            )}
            <Controls
              position="bottom-left"
              showInteractive={false}
              fitViewOptions={defaultFitViewOptions}
              className="launchpad-flow-controls !mb-3 !ml-3"
            />
            <MiniMap
              position="bottom-right"
              pannable
              zoomable
              ariaLabel="Workflow minimap"
              className="launchpad-flow-minimap"
              nodeColor={(n) => {
                const d = n.data as FlowNodeData;
                if (d?.isActive) return "#60a5fa";
                if (d?.runtime?.status === "success") return "#34d399";
                if (d?.componentKind === "agent") return "#22c55e";
                if (d?.componentKind === "tool") return "#3b82f6";
                if (d?.componentKind === "function") return "#a855f7";
                const k = d?.kind;
                if (k === "input") return "#38bdf8";
                if (k === "orchestrator") return "#8b5cf6";
                if (k?.startsWith("agent-")) return "#22c55e";
                if (k === "human") return "#f97316";
                return "#64748b";
              }}
              maskColor="rgba(6, 10, 16, 0.9)"
              maskStrokeColor="rgba(59, 130, 246, 0.35)"
              maskStrokeWidth={1}
            />
          </ReactFlow>
        </div>

        {!fullscreen && !builderShell && (
        <aside className="w-[7.5rem] flex-shrink-0 border-l border-border bg-panel/80 p-1.5">
          <SimulationPanel
            state={simulationState}
            onRun={run}
            onStop={stop}
            disabled={!plan || layoutLoading}
          />
        </aside>
        )}
      </div>
    </div>
  );
}

export function ArchitectureFlowView({
  plan,
  builderShell = false,
}: {
  plan: ArchitecturePlan | null;
  builderShell?: boolean;
}) {
  if (!plan?.nodes?.length) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-slate-500">
        No architecture graph — generate a plan first.
      </div>
    );
  }

  return (
    <ReactFlowProvider>
      <FlowInner plan={plan} builderShell={builderShell} />
    </ReactFlowProvider>
  );
}
