import { useCallback, useEffect, useRef, useState } from "react";
import {
  applyEdgeChanges,
  applyNodeChanges,
  type Edge,
  type Node,
  type OnEdgesChange,
  type OnNodesChange,
} from "@xyflow/react";
import type { ArchitecturePlan, FlowEdgeData, FlowNodeData } from "@/architecture-flow/types/plan";
import { buildGraphStructure, type GraphStructure } from "@/architecture-flow/lib/buildGraphStructure";
import { calculateLayout, type LayoutMeta } from "@/architecture-flow/layout/calculateLayout";

function walkOrder(nodes: Node<FlowNodeData>[], edges: Edge<FlowEdgeData>[]): string[] {
  const layoutNodes = nodes.filter(
    (n) =>
      !n.id.startsWith("__lane_") &&
      n.type !== "laneLabel" &&
      n.type !== "laneBand" &&
      n.type !== "parallelGroup",
  );
  return [...layoutNodes]
    .sort(
      (a, b) =>
        (a.data.pipelineOrder ?? 0) - (b.data.pipelineOrder ?? 0) ||
        a.id.localeCompare(b.id),
    )
    .map((n) => n.id);
}

function isLayoutNode(n: Node<FlowNodeData>): boolean {
  return (
    !n.id.startsWith("__lane_") &&
    n.type !== "laneBand" &&
    !(n.type === "parallelGroup" && n.id.startsWith("__parallel_bg_"))
  );
}

export interface SimulationState {
  simulating: boolean;
  stepIndex: number;
  stepTotal: number;
  currentStepLabel: string;
  currentStepId: string | null;
  progress: number;
}

export function useSimulation(plan: ArchitecturePlan | null) {
  const [nodes, setNodes] = useState<Node<FlowNodeData>[]>([]);
  const [edges, setEdges] = useState<Edge<FlowEdgeData>[]>([]);
  const [simulating, setSimulating] = useState(false);
  const [stepIndex, setStepIndex] = useState(-1);
  const [stepTotal, setStepTotal] = useState(0);
  const [currentStepId, setCurrentStepId] = useState<string | null>(null);
  const [currentStepLabel, setCurrentStepLabel] = useState("");
  const [layoutLoading, setLayoutLoading] = useState(false);
  const [layoutMeta, setLayoutMeta] = useState<LayoutMeta | null>(null);
  const orderRef = useRef<string[]>([]);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const structureRef = useRef<GraphStructure | null>(null);

  const runLayout = useCallback(
    async (structure: GraphStructure, nodeOverrides?: Node<FlowNodeData>[]) => {
      setLayoutLoading(true);
      try {
        const baseNodes = nodeOverrides ?? structure.nodes;
        const { nodes: laid, meta } = await calculateLayout(
          baseNodes,
          structure.edges,
          structure.parallel
        );
        setNodes(laid);
        setEdges(structure.edges);
        setLayoutMeta(meta);
        orderRef.current = walkOrder(laid, structure.edges);
      } finally {
        setLayoutLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    if (!plan) {
      setNodes([]);
      setEdges([]);
      setLayoutMeta(null);
      structureRef.current = null;
      return;
    }
    let cancelled = false;
    (async () => {
      const structure = buildGraphStructure(plan, { includeLaneChrome: false });
      if (cancelled) return;
      structureRef.current = structure;
      await runLayout(structure);
    })();
    return () => {
      cancelled = true;
    };
  }, [plan, runLayout]);

  const applyHighlight = useCallback((activeId: string | null, simActive: boolean) => {
    const activeIdx = activeId ? orderRef.current.indexOf(activeId) : -1;
    setNodes((nds) =>
      nds.map((n) => {
        const idx = orderRef.current.indexOf(n.id);
        const isActive = n.id === activeId;
        const status =
          !simActive || !isLayoutNode(n)
            ? "idle"
            : isActive
              ? "running"
              : idx >= 0 && activeIdx >= 0 && idx < activeIdx
                ? "success"
                : "idle";
        const isDimmed = simActive && isLayoutNode(n) && status === "idle";
        return {
          ...n,
          zIndex: isActive ? 20 : isDimmed ? 0 : 5,
          data: {
            ...n.data,
            isActive,
            isDimmed,
            isHighlighted: false,
            runtime: {
              ...n.data.runtime,
              status,
            },
          },
        };
      })
    );
    setEdges((eds) =>
      eds.map((e) => {
        const isOutgoing = activeId ? e.source === activeId : false;
        const isIncoming = activeId ? e.target === activeId : false;
        return {
          ...e,
          zIndex: isOutgoing || isIncoming ? 10 : 0,
          data: {
            edgeKind: e.data?.edgeKind ?? "sequential",
            label: e.data?.label,
            animated: e.data?.animated,
            isActive: isOutgoing || isIncoming,
            isFlowing: isOutgoing,
          },
        };
      })
    );
  }, []);

  const stop = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setSimulating(false);
    setStepIndex(-1);
    setCurrentStepId(null);
    setCurrentStepLabel("");
    applyHighlight(null, false);
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        zIndex: undefined,
        data: {
          ...n.data,
          isActive: false,
          isDimmed: false,
          runtime: { ...n.data.runtime, status: "idle" },
        },
      }))
    );
    setEdges((eds) =>
      eds.map((e) => ({
        ...e,
        zIndex: undefined,
        data: {
          edgeKind: e.data?.edgeKind ?? "sequential",
          label: e.data?.label,
          animated: e.data?.animated,
          isActive: false,
          isFlowing: false,
        },
      }))
    );
  }, [applyHighlight]);

  const run = useCallback(() => {
    stop();
    const order = orderRef.current.filter((id) => {
      const n = nodes.find((x) => x.id === id);
      return n && isLayoutNode(n);
    });
    if (!order.length) return;
    setStepTotal(order.length);
    setSimulating(true);
    let i = 0;
    const tick = () => {
      if (i >= order.length) {
        setSimulating(false);
        setStepIndex(order.length);
        setCurrentStepId(null);
        setCurrentStepLabel("Complete");
        applyHighlight(null, false);
        setNodes((nds) =>
          nds.map((n) => ({
            ...n,
            data: {
              ...n.data,
              isDimmed: false,
              runtime: { ...n.data.runtime, status: "success" },
              isActive: false,
            },
          }))
        );
        window.dispatchEvent(
          new CustomEvent("launchpad:simulation-step", {
            detail: { stepIndex: order.length, stepTotal: order.length, nodeId: null, label: "Complete" },
          })
        );
        return;
      }
      const stepId = order[i];
      const stepNode = nodes.find((x) => x.id === stepId);
      const label = stepNode?.data.label ?? stepId;
      setStepIndex(i);
      setCurrentStepId(stepId);
      setCurrentStepLabel(label);
      applyHighlight(stepId, true);
      window.dispatchEvent(
        new CustomEvent("launchpad:simulation-step", {
          detail: { stepIndex: i, stepTotal: order.length, nodeId: stepId, label },
        })
      );
      i += 1;
      timerRef.current = setTimeout(tick, 1100);
    };
    tick();
  }, [applyHighlight, nodes, stop]);

  const toggleExpand = useCallback(
    (nodeId: string) => {
      setNodes((nds) => {
        const updated = nds.map((n) =>
          n.id === nodeId ? { ...n, data: { ...n.data, expanded: !n.data.expanded } } : n
        );
        const structure = structureRef.current;
        if (structure) {
          const forLayout = updated.filter(
            (n) =>
              isLayoutNode(n) ||
              n.id.startsWith("__lane_") ||
              n.type === "laneBand" ||
              (n.type === "parallelGroup" && n.id.startsWith("__parallel_bg_"))
          );
          void calculateLayout(forLayout, structure.edges, structure.parallel).then(
            ({ nodes: laid, meta }) => {
              setNodes(laid);
              setLayoutMeta(meta);
            }
          );
        }
        return updated;
      });
    },
    []
  );

  const selectNode = useCallback((nodeId: string | null) => {
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        data: { ...n.data, isHighlighted: nodeId ? n.id === nodeId : false },
      }))
    );
  }, []);

  const onNodesChange: OnNodesChange = useCallback((changes) => {
    setNodes((nds) => applyNodeChanges(changes, nds) as Node<FlowNodeData>[]);
  }, []);

  const onEdgesChange: OnEdgesChange = useCallback((changes) => {
    setEdges((eds) => applyEdgeChanges(changes, eds) as Edge<FlowEdgeData>[]);
  }, []);

  const progress =
    stepTotal > 0 ? Math.min(1, (stepIndex + (simulating ? 0.35 : 0)) / stepTotal) : 0;

  const simulationState: SimulationState = {
    simulating,
    stepIndex,
    stepTotal,
    currentStepLabel,
    currentStepId,
    progress,
  };

  return {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    simulating,
    stepIndex,
    stepTotal,
    currentStepId,
    currentStepLabel,
    simulationState,
    layoutLoading,
    layoutMeta,
    run,
    stop,
    toggleExpand,
    selectNode,
  };
}
