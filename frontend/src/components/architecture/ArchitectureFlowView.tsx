import { useCallback, useEffect, useMemo, useState } from "react";
import { DEBUG_LAYOUT } from "@/layout/constants";
import { LayoutDebugOverlay } from "@/components/layout/LayoutDebugOverlay";
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

import type { ArchitecturePlan, FlowNodeData } from "@/types/plan";
import { useSimulation } from "@/hooks/useSimulation";
import { useGraphViewport } from "@/hooks/useGraphViewport";
import { defaultFitViewOptions } from "@/layout/viewport";
import { AnimatedEdge } from "@/components/edges/AnimatedEdge";
import { InputNode } from "@/components/nodes/InputNode";
import { OrchestratorNode } from "@/components/nodes/OrchestratorNode";
import { AgentNode } from "@/components/nodes/AgentNode";
import { MergeNode } from "@/components/nodes/MergeNode";
import { HumanNode } from "@/components/nodes/HumanNode";
import { ParallelGroupNode } from "@/components/nodes/ParallelGroupNode";
import { LaneLabelNode } from "@/components/nodes/LaneLabelNode";
import { LaneBandNode } from "@/components/nodes/LaneBandNode";
import { MetricsPanel } from "@/components/panels/MetricsPanel";
import { NodeDetailPanel } from "@/components/panels/NodeDetailPanel";

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

function FlowInner({
  plan,
  onStats,
}: {
  plan: ArchitecturePlan | null;
  onStats?: (s: ReturnType<typeof useSimulation>["stats"]) => void;
}) {
  const {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    simulating,
    stepIndex,
    run,
    stop,
    toggleExpand,
    selectNode,
    stats,
    layoutLoading,
    layoutMeta,
  } = useSimulation(plan);

  const { translateExtent, applyFit, focusNode, viewportConfig } = useGraphViewport(
    nodes,
    layoutLoading,
    layoutMeta
  );

  const [selected, setSelected] = useState<FlowNodeData | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [layoutDebug, setLayoutDebug] = useState(DEBUG_LAYOUT);

  useEffect(() => {
    onStats?.(stats);
  }, [stats, onStats]);

  useEffect(() => {
    const handler = (e: Event) => {
      const id = (e as CustomEvent<{ nodeId: string }>).detail?.nodeId;
      if (id) {
        selectNode(id);
        setSelectedId(id);
        const n = nodes.find((x) => x.id === id);
        if (n) setSelected(n.data);
        focusNode(id);
      }
    };
    window.addEventListener("launchpad:select-node", handler);
    return () => window.removeEventListener("launchpad:select-node", handler);
  }, [nodes, selectNode, focusNode]);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node<FlowNodeData>) => {
      if (node.id.startsWith("__lane_") || node.type === "laneBand") return;
      setSelected(node.data);
      setSelectedId(node.id);
      selectNode(node.id);
      if (node.type?.toString().startsWith("agent")) {
        toggleExpand(node.id);
      }
    },
    [selectNode, toggleExpand]
  );

  const onPaneClick = useCallback(() => {
    setSelected(null);
    setSelectedId(null);
    selectNode(null);
  }, [selectNode]);

  const defaultEdgeOptions = useMemo(
    () => ({ type: "animated" as const, animated: true }),
    []
  );

  const graphSizeHint = layoutMeta
    ? `${Math.round(layoutMeta.bounds.width)}×${Math.round(layoutMeta.bounds.height)}px canvas · pan to explore`
    : "Pan · scroll to zoom";

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex flex-shrink-0 flex-wrap items-center justify-between gap-2 border-b border-border bg-panel/60 px-3 py-2 backdrop-blur-md">
        <div className="flex flex-col gap-0.5">
          <span className="text-xs font-semibold uppercase tracking-widest text-slate-400">
            AI Workflow Graph
          </span>
          <span className="text-[10px] text-slate-500">{graphSizeHint}</span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {simulating && (
            <span className="rounded-full bg-blue-500/20 px-2 py-0.5 text-[10px] text-blue-300">
              Live simulation
            </span>
          )}
          {layoutLoading && (
            <span className="rounded-full bg-slate-500/20 px-2 py-0.5 text-[10px] text-slate-400">
              Layout…
            </span>
          )}
          <button
            type="button"
            onClick={run}
            disabled={!plan || simulating}
            className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-40"
          >
            Run simulation
          </button>
          <button
            type="button"
            onClick={stop}
            disabled={!simulating}
            className="rounded-lg border border-border bg-white/5 px-3 py-1.5 text-xs text-slate-300 hover:bg-white/10 disabled:opacity-40"
          >
            Stop
          </button>
          <button
            type="button"
            onClick={() => void applyFit("full")}
            className="rounded-lg border border-border bg-white/5 px-3 py-1.5 text-xs text-slate-300 hover:bg-white/10"
            title="Fit entire workflow (readable zoom floor)"
          >
            Fit all
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

      <div className="flex flex-1 min-h-0 min-w-0">
        <div className="launchpad-flow-canvas relative min-h-0 min-w-0 flex-1">
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
            <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="#1e293b" />
            <LayoutDebugOverlay enabled={layoutDebug} />
            <Panel position="top-left" className="!m-2 !p-0">
              <div className="rounded-md border border-border/80 bg-panel/90 px-2 py-1 text-[10px] text-slate-500 backdrop-blur-sm">
                Drag to pan · Wheel / pinch to zoom
              </div>
            </Panel>
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
                const k = (n.data as FlowNodeData)?.kind;
                if (k === "orchestrator") return "#3b82f6";
                if (k?.startsWith("agent-reuse")) return "#22c55e";
                if (k === "human") return "#f97316";
                if (k === "merge" || k === "decision") return "#a855f7";
                return "#64748b";
              }}
              maskColor="rgba(6, 10, 16, 0.9)"
              maskStrokeColor="rgba(59, 130, 246, 0.35)"
              maskStrokeWidth={1}
            />
          </ReactFlow>
        </div>

        <aside className="w-72 flex-shrink-0 border-l border-border bg-panel/90 backdrop-blur-xl overflow-y-auto p-4 space-y-6">
          <section>
            <h3 className="mb-2 text-[10px] font-bold uppercase tracking-widest text-slate-500">
              Pipeline metrics
            </h3>
            <MetricsPanel
              plan={plan}
              stats={stats}
              simulating={simulating}
              stepIndex={stepIndex}
            />
          </section>
          <section>
            <h3 className="mb-2 text-[10px] font-bold uppercase tracking-widest text-slate-500">
              Node inspector
            </h3>
            <NodeDetailPanel node={selected} />
          </section>
          <section>
            <h3 className="mb-2 text-[10px] font-bold uppercase tracking-widest text-slate-500">
              Legend
            </h3>
            <ul className="space-y-1.5 text-xs text-slate-400">
              <li className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-emerald-400" /> Reuse catalog agent
              </li>
              <li className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-teal-400" /> Adapt existing
              </li>
              <li className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-indigo-400" /> Build new
              </li>
              <li className="flex items-center gap-2">
                <span className="h-2 w-3 border-t-2 border-dashed border-cyan-400" /> Parallel branch
              </li>
              <li className="flex items-center gap-2">
                <span className="h-2 w-3 border-t-2 border-dotted border-orange-400" /> Retry / HITL
              </li>
            </ul>
          </section>
        </aside>
      </div>
    </div>
  );
}

export function ArchitectureFlowView({
  plan,
  onStats,
}: {
  plan: ArchitecturePlan | null;
  onStats?: (s: ReturnType<typeof useSimulation>["stats"]) => void;
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
      <FlowInner plan={plan} onStats={onStats} />
    </ReactFlowProvider>
  );
}
