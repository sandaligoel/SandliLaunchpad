import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "@tanstack/react-router";
import {
  Background,
  BackgroundVariant,
  MiniMap,
  ReactFlow,
  addEdge,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type EdgeTypes,
  type Node,
  type NodeMouseHandler,
  type NodeTypes,
  type OnConnect,
  type OnEdgesChange,
  type OnNodesChange,
} from "@xyflow/react";
import {
  generateArchitecture,
  getSession,
} from "@/api/affine/client";
import {
  loadBuilderWorkflowAsync,
  saveBuilderWorkflowAsync,
  setActiveBuilderSessionId,
  type SavedBuilderWorkflow,
} from "@/api/affine/builderStorage";
import { setStoredSessionId } from "@/api/affine/sessionStorage";
import type { ArchitecturePlan, ReuseDecisionType } from "@/api/affine/types";
import { LaunchpadAgentPalette } from "@/components/canvas/LaunchpadAgentPalette";
import LaunchpadPlanNode from "@/components/canvas/LaunchpadPlanNode";
import { FlowPipelineEdge } from "@/components/canvas/FlowPipelineEdge";
import { FitWorkflowView } from "@/components/canvas/FitWorkflowView";
import { WorkflowCanvasControls } from "@/components/canvas/WorkflowCanvasControls";
import { useWorkflowFitAll } from "@/hooks/useWorkflowFitAll";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { layoutGraphToFlow } from "@/utils/graphLayout";
import { syncFlowEdgesToPlan, updatePlanStep } from "@/utils/planFlowSync";
import { sanitizeArchitecturePlan } from "@/utils/sanitizePlan";
import {
  workflowDefaultEdgeOptions,
  workflowZoomConfig,
} from "@/utils/flowEdgeStyles";
import { useWorkflowPresentation } from "@/context/WorkflowPresentationContext";
import { PresentationFitEffect } from "@/components/canvas/PresentationFitEffect";
import { WorkflowNodeMeasureEffect } from "@/components/canvas/WorkflowNodeMeasureEffect";
import { Loader2, Pencil } from "lucide-react";

const nodeTypes: NodeTypes = { launchpad: LaunchpadPlanNode as never };
const edgeTypes: EdgeTypes = { pipeline: FlowPipelineEdge };

const SAVE_DEBOUNCE_MS = 400;

export function LaunchpadBuilder({ sessionId }: { sessionId: string }) {
  const [plan, setPlan] = useState<ArchitecturePlan | null>(null);
  const [problemStatement, setProblemStatement] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [positionOverrides, setPositionOverrides] = useState<
    Record<string, { x: number; y: number }>
  >({});
  const [savedHint, setSavedHint] = useState(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const presentation = useWorkflowPresentation();
  const isPresentation = presentation?.isPresentation ?? false;

  useEffect(() => {
    if (!isPresentation) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [isPresentation]);

  const persistLocal = useCallback(
    (
      nextPlan: ArchitecturePlan,
      flowNodes: { id: string; position: { x: number; y: number } }[],
      selected: string | null,
    ) => {
      const nodePositions = Object.fromEntries(
        flowNodes.map((n) => [n.id, n.position]),
      );
      const payload: SavedBuilderWorkflow = {
        sessionId,
        plan: nextPlan,
        nodePositions,
        selectedNodeId: selected,
        title: problemStatement.slice(0, 72) + (problemStatement.length > 72 ? "…" : ""),
        problemStatement,
        savedAt: new Date().toISOString(),
      };
      void saveBuilderWorkflowAsync(payload).then(() => {
        setPositionOverrides(nodePositions);
        setSavedHint(true);
      });
    },
    [sessionId, problemStatement],
  );

  const schedulePersist = useCallback(
    (
      nextPlan: ArchitecturePlan,
      flowNodes: { id: string; position: { x: number; y: number } }[],
      selected: string | null,
    ) => {
      if (saveTimer.current) clearTimeout(saveTimer.current);
      saveTimer.current = setTimeout(() => {
        void persistLocal(nextPlan, flowNodes, selected);
      }, SAVE_DEBOUNCE_MS);
    },
    [persistLocal],
  );

  useEffect(() => {
    let cancelled = false;
    setActiveBuilderSessionId(sessionId);

    const applySaved = (saved: SavedBuilderWorkflow) => {
      const cleaned = sanitizeArchitecturePlan(saved.plan);
      setPlan(cleaned);
      setPositionOverrides(saved.nodePositions ?? {});
      setSelectedNodeId(saved.selectedNodeId ?? null);
      if (saved.problemStatement) setProblemStatement(saved.problemStatement);
      setSavedHint(true);
    };

    const snapshotPlan = (
      nextPlan: ArchitecturePlan,
      ps: string,
      overrides: Record<string, { x: number; y: number }> = {},
      selected: string | null = null,
    ) => {
      void saveBuilderWorkflowAsync({
        sessionId,
        plan: nextPlan,
        nodePositions: overrides,
        selectedNodeId: selected,
        problemStatement: ps,
        title: ps.slice(0, 72) + (ps.length > 72 ? "…" : ""),
        savedAt: new Date().toISOString(),
      });
    };

    (async () => {
      setLoading(true);
      setError(null);
      try {
        const { session } = await getSession(sessionId);
        if (cancelled) return;
        const ps = session.spec.problem_statement;
        setProblemStatement(ps);

        const saved = await loadBuilderWorkflowAsync(sessionId);
        if (saved?.plan?.graph?.nodes?.length) {
          applySaved(saved);
          return;
        }

        if (session.architecture_plan?.graph?.nodes?.length) {
          const cleaned = sanitizeArchitecturePlan(session.architecture_plan);
          setPlan(cleaned);
          setPositionOverrides({});
          snapshotPlan(cleaned, ps);
          return;
        }

        const canPlan = session.spec.status === "ready";
        if (!canPlan) {
          setError(
            "Finish the Agent Launchpad interview first, then return here to edit your workflow.",
          );
          return;
        }
        const { plan: p } = await generateArchitecture(sessionId, false);
        if (!cancelled) {
          const cleaned = sanitizeArchitecturePlan(p);
          setPlan(cleaned);
          setPositionOverrides({});
          snapshotPlan(cleaned, ps);
        }
      } catch (e) {
        if (cancelled) return;
        const fallback = await loadBuilderWorkflowAsync(sessionId);
        if (fallback?.plan?.graph?.nodes?.length) {
          applySaved(fallback);
          return;
        }
        setError(
          e instanceof Error ? e.message : "Failed to load architecture",
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const layout = useMemo(() => {
    if (!plan?.graph?.nodes?.length) return { nodes: [], edges: [] };
    return layoutGraphToFlow(
      plan.graph,
      plan.reuse_decisions,
      selectedNodeId,
      plan.validation?.node_status ?? {},
      positionOverrides,
    );
  }, [plan, selectedNodeId, positionOverrides]);

  const [nodes, setNodes, onNodesChange] = useNodesState(layout.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(layout.edges);
  const skipLayoutSync = useRef(false);

  useEffect(() => {
    if (skipLayoutSync.current) {
      skipLayoutSync.current = false;
      return;
    }
    setNodes(layout.nodes);
    setEdges(layout.edges);
  }, [layout, setNodes, setEdges]);

  const focusNode = useCallback(
    (nodeId: string) => {
      setSelectedNodeId(nodeId);
      setNodes((nds) =>
        nds.map((n) => ({
          ...n,
          selected: n.id === nodeId,
          data: { ...n.data, selected: n.id === nodeId },
        })),
      );
      if (plan) {
        schedulePersist(plan, nodes, nodeId);
      }
    },
    [setNodes, plan, schedulePersist, nodes],
  );

  const patchPlan = useCallback(
    (nextPlan: ArchitecturePlan, nextEdges?: Edge[]) => {
      skipLayoutSync.current = true;
      setPlan(nextPlan);
      const edgeList = nextEdges ?? edges;
      schedulePersist(
        nextPlan,
        nodes.map((n) => ({ id: n.id, position: n.position })),
        selectedNodeId,
      );
      if (nextEdges) setEdges(nextEdges);
    },
    [edges, nodes, selectedNodeId, schedulePersist, setEdges],
  );

  const onConnect = useCallback(
    (connection: Connection) => {
      if (!plan || !connection.source || !connection.target) return;
      setEdges((eds) => {
        const nextEdges = addEdge(connection, eds);
        const nextPlan = syncFlowEdgesToPlan(plan, nextEdges);
        patchPlan(nextPlan, nextEdges);
        return nextEdges;
      });
    },
    [plan, patchPlan, setEdges],
  );

  useEffect(() => {
    if (!plan || nodes.length === 0) return;
    schedulePersist(
      plan,
      nodes.map((n) => ({ id: n.id, position: n.position })),
      selectedNodeId,
    );
  }, [nodes, plan, selectedNodeId, schedulePersist]);

  const selectedDecision = plan?.reuse_decisions.find(
    (d) => d.node_id === selectedNodeId,
  );

  const updateSelectedStep = useCallback(
    (patch: {
      node_label?: string;
      decision?: ReuseDecisionType;
      rationale?: string;
    }) => {
      if (!plan || !selectedNodeId) return;
      const nextPlan = updatePlanStep(plan, selectedNodeId, patch);
      setNodes((nds) =>
        nds.map((n) =>
          n.id === selectedNodeId
            ? {
                ...n,
                data: {
                  ...n.data,
                  label: patch.node_label ?? n.data.label,
                  decision: patch.decision ?? n.data.decision,
                  rationale: patch.rationale ?? n.data.rationale,
                },
              }
            : n,
        ),
      );
      patchPlan(nextPlan);
    },
    [plan, selectedNodeId, patchPlan, setNodes],
  );

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3 p-8">
        <Loader2 className="animate-spin text-primary" size={28} />
        <p className="text-sm text-muted-foreground">
          Building your architecture from the interview… (30–60s)
        </p>
      </div>
    );
  }

  if (error || !plan) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-4 p-8 max-w-md text-center">
        <p className="text-sm text-destructive">
          {error ?? "No architecture plan"}
        </p>
        <Link to="/interview" className="text-sm text-primary underline">
          Back to Agent Launchpad
        </Link>
      </div>
    );
  }

  const title =
    problemStatement.slice(0, 48) +
    (problemStatement.length > 48 ? "…" : "");

  const flowCanvas = (
    <LaunchpadFlowCanvas
      isPresentation={isPresentation}
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      onNodeClick={(_, n) => focusNode(n.id)}
      onPaneClick={() => {
        setSelectedNodeId(null);
        if (plan) {
          schedulePersist(
            plan,
            nodes.map((n) => ({ id: n.id, position: n.position })),
            null,
          );
        }
      }}
      nodeCount={layout.nodes.length}
      edgeTypes={edgeTypes}
    />
  );

  return (
    <>
      {!isPresentation ? (
      <div className="h-14 border-b border-border bg-surface px-4 flex items-center gap-3 shrink-0">
        <div className="min-w-0 flex-1">
          <div className="text-sm font-semibold truncate">
            {title || "Launchpad workflow"}
          </div>
          <div className="text-[11px] text-muted-foreground flex items-center gap-2">
            <span>
              {plan.graph.nodes.length} steps ·{" "}
              {
                plan.reuse_decisions.filter(
                  (d) => d.decision === "reuse" || d.decision === "adapt",
                ).length
              }{" "}
              reuse ·{" "}
              {plan.reuse_decisions.filter((d) => d.decision === "build").length}{" "}
              build
            </span>
            <span className="inline-flex items-center gap-1 text-primary">
              <Pencil size={11} />
              Edit flow
            </span>
            {savedHint ? (
              <span className="text-muted-foreground">· Saved locally</span>
            ) : null}
          </div>
        </div>
        <Button variant="outline" size="sm" asChild>
          <Link
            to="/interview"
            search={{ sessionId, view: "chat" }}
            onClick={() => setStoredSessionId(sessionId)}
          >
            Chat history
          </Link>
        </Button>
      </div>
      ) : null}
      <div className={isPresentation ? "" : "flex-1 flex min-h-0"}>
        {!isPresentation ? (
          <LaunchpadAgentPalette plan={plan} onFocusNode={focusNode} />
        ) : null}
        {flowCanvas}
        {!isPresentation ? (
        <aside className="w-80 shrink-0 border-l border-border bg-surface p-4 overflow-y-auto flex flex-col gap-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Step details
          </h3>
          {selectedDecision ? (
            <div className="space-y-3 text-sm">
              <div>
                <label className="text-[11px] text-muted-foreground block mb-1">
                  Step name
                </label>
                <Input
                  value={selectedDecision.node_label}
                  onChange={(e) =>
                    updateSelectedStep({ node_label: e.target.value })
                  }
                />
              </div>
              <div>
                <label className="text-[11px] text-muted-foreground block mb-1">
                  Catalog decision
                </label>
                <select
                  className="w-full h-9 rounded-md border border-border bg-background px-2 text-sm"
                  value={selectedDecision.decision}
                  onChange={(e) =>
                    updateSelectedStep({
                      decision: e.target.value as ReuseDecisionType,
                    })
                  }
                >
                  <option value="reuse">Reuse from catalog</option>
                  <option value="adapt">Adapt catalog agent</option>
                  <option value="build">Build new</option>
                </select>
              </div>
              {selectedDecision.agent_name ? (
                <p className="text-xs text-muted-foreground">
                  Suggested catalog match: {selectedDecision.agent_name}
                </p>
              ) : null}
              <div>
                <label className="text-[11px] text-muted-foreground block mb-1">
                  Notes
                </label>
                <Textarea
                  rows={4}
                  value={selectedDecision.rationale}
                  onChange={(e) =>
                    updateSelectedStep({ rationale: e.target.value })
                  }
                />
              </div>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">
              Click a step to edit it. Drag nodes to rearrange; connect handles
              to add flow links. Saved automatically — find past workflows on
              the Workflows tab.
            </p>
          )}
        </aside>
        ) : null}
      </div>
    </>
  );
}

function LaunchpadFlowCanvas({
  isPresentation,
  nodes,
  edges,
  nodeTypes,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onNodeClick,
  onPaneClick,
  nodeCount,
  edgeTypes,
}: {
  isPresentation: boolean;
  nodes: Node[];
  edges: Edge[];
  nodeTypes: NodeTypes;
  edgeTypes: EdgeTypes;
  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  onConnect: OnConnect;
  onNodeClick: NodeMouseHandler;
  onPaneClick: () => void;
  nodeCount: number;
}) {
  const onFitAll = useWorkflowFitAll();

  return (
    <div
      className={
        isPresentation
          ? "workflow-canvas workflow-canvas--presentation fixed inset-0 z-[300]"
          : "workflow-canvas flex-1 min-h-0 relative"
      }
    >
      <div className="absolute inset-0">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          defaultEdgeOptions={workflowDefaultEdgeOptions}
          connectionLineStyle={{
            stroke: "#4f46e5",
            strokeWidth: 2.5,
            strokeLinecap: "round",
            strokeLinejoin: "round",
          }}
          defaultMarkerColor="#0d9488"
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          nodesDraggable
          nodesConnectable
          elementsSelectable
          snapToGrid
          snapGrid={[24, 24]}
          elevateEdgesOnSelect
          minZoom={workflowZoomConfig.minZoom}
          maxZoom={workflowZoomConfig.maxZoom}
          zoomOnScroll
          zoomOnPinch
          zoomOnDoubleClick={false}
          zoomOnScrollSpeed={workflowZoomConfig.zoomOnScrollSpeed}
          panOnScroll={false}
          proOptions={{ hideAttribution: true }}
        >
          <PresentationFitEffect />
          <WorkflowNodeMeasureEffect nodeIds={nodes.map((n) => n.id)} />
          <FitWorkflowView nodeCount={nodeCount} />
          <Background
            variant={BackgroundVariant.Dots}
            gap={22}
            size={1.25}
            color="#94a3b8"
            className="workflow-canvas-dots"
          />
          {!isPresentation ? (
            <MiniMap
              className="workflow-minimap !rounded-xl !border !border-slate-200/90 !shadow-lg"
              zoomable
              pannable
              maskColor="rgba(238, 242, 248, 0.75)"
              nodeColor={(n) => {
                const d = n.data as { nodeType?: string; decision?: string };
                if (d.decision === "reuse") return "#059669";
                if (d.decision === "adapt") return "#0284c7";
                if (d.nodeType === "gateway") return "#d97706";
                if (d.nodeType === "human") return "#059669";
                return "#4f46e5";
              }}
            />
          ) : null}
        </ReactFlow>
      </div>
      <WorkflowCanvasControls onFitAll={onFitAll} />
    </div>
  );
}
