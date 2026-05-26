import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "@tanstack/react-router";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  addEdge,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type NodeTypes,
} from "@xyflow/react";
import {
  generateArchitecture,
  getSession,
} from "@/api/affine/client";
import {
  loadBuilderWorkflowAsync,
  saveBuilderWorkflow,
  setActiveBuilderSessionId,
  type SavedBuilderWorkflow,
} from "@/api/affine/builderStorage";
import { setStoredSessionId } from "@/api/affine/sessionStorage";
import type { ArchitecturePlan, ReuseDecisionType } from "@/api/affine/types";
import { LaunchpadAgentPalette } from "@/components/canvas/LaunchpadAgentPalette";
import LaunchpadPlanNode from "@/components/canvas/LaunchpadPlanNode";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { layoutGraphToFlow } from "@/utils/graphLayout";
import { syncFlowEdgesToPlan, updatePlanStep } from "@/utils/planFlowSync";
import { Loader2, Pencil } from "lucide-react";

const nodeTypes: NodeTypes = { launchpad: LaunchpadPlanNode as never };

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
      saveBuilderWorkflow(payload);
      setPositionOverrides(nodePositions);
      setSavedHint(true);
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
        persistLocal(nextPlan, flowNodes, selected);
      }, SAVE_DEBOUNCE_MS);
    },
    [persistLocal],
  );

  useEffect(() => {
    let cancelled = false;
    setActiveBuilderSessionId(sessionId);

    const applySaved = (saved: SavedBuilderWorkflow) => {
      setPlan(saved.plan);
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
      saveBuilderWorkflow({
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
      const saved = await loadBuilderWorkflowAsync(sessionId);

      if (saved?.plan?.graph?.nodes?.length) {
        applySaved(saved);
        setLoading(false);
        try {
          const { session } = await getSession(sessionId);
          if (!cancelled && session.spec.problem_statement) {
            setProblemStatement(session.spec.problem_statement);
          }
        } catch {
          /* keep local snapshot if API unavailable */
        }
        return;
      }

      try {
        const { session } = await getSession(sessionId);
        if (cancelled) return;
        const ps = session.spec.problem_statement;
        setProblemStatement(ps);

        if (session.architecture_plan?.graph?.nodes?.length) {
          setPlan(session.architecture_plan);
          snapshotPlan(session.architecture_plan, ps);
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
          setPlan(p);
          snapshotPlan(p, ps);
        }
      } catch (e) {
        if (cancelled) return;
        if (saved?.plan?.graph?.nodes?.length) {
          applySaved(saved);
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

  return (
    <>
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
      <div className="flex-1 flex min-h-0">
        <LaunchpadAgentPalette plan={plan} onFocusNode={focusNode} />
        <div className="flex-1 flex flex-col min-w-0 relative bg-background">
          <ReactFlow
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
            nodesDraggable
            nodesConnectable
            elementsSelectable
            fitView
            proOptions={{ hideAttribution: true }}
          >
            <Background gap={18} size={1} color="#E5E7EB" />
            <MiniMap className="!bg-surface !border !border-border" />
            <Controls className="!bg-surface !border-border" />
          </ReactFlow>
        </div>
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
      </div>
    </>
  );
}
