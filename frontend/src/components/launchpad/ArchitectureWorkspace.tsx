import { useCallback, useEffect, useMemo, useState, type MouseEvent } from "react";
import {
  Background,
  Controls,
  MiniMap,
  Panel,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import type { ArchitecturePlan } from "@/api/affine/types";
import { useAgents } from "@/api/hooks";
import { computeFlowOrder } from "@/utils/flowOrder";
import { layoutGraphToFlow } from "@/utils/graphLayout";
import { buildNodeIoMap } from "@/utils/stepIo";
import { ArchitectureInspector } from "./ArchitectureInspector";
import ArchitectureNode from "./ArchitectureNode";

const nodeTypes = { architecture: ArchitectureNode };

interface Props {
  sessionId: string;
  plan: ArchitecturePlan | null;
  loading: boolean;
  error: string | null;
  canGenerate: boolean;
  onGenerate: (force?: boolean) => void;
  onPlanUpdated: (plan: ArchitecturePlan) => void;
  onBackToSpec: () => void;
}

export function ArchitectureWorkspace({
  sessionId,
  plan,
  loading,
  error,
  canGenerate,
  onGenerate,
  onPlanUpdated,
  onBackToSpec,
}: Props) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const { data: catalogAgents = [] } = useAgents();

  const flowOrder = useMemo(
    () => (plan?.graph ? computeFlowOrder(plan.graph) : []),
    [plan],
  );

  const nodeIo = useMemo(
    () => (plan ? buildNodeIoMap(plan, catalogAgents) : {}),
    [plan, catalogAgents],
  );

  const layout = useMemo(() => {
    if (!plan?.graph?.nodes?.length) return { nodes: [], edges: [] };
    return layoutGraphToFlow(
      plan.graph,
      plan.reuse_decisions,
      selectedNodeId,
      plan.validation?.node_status ?? {},
      undefined,
      nodeIo,
    );
  }, [plan, selectedNodeId, nodeIo]);

  const [nodes, setNodes, onNodesChange] = useNodesState(layout.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(layout.edges);

  useEffect(() => {
    setNodes(layout.nodes);
    setEdges(layout.edges);
  }, [layout, setNodes, setEdges]);

  useEffect(() => {
    if (plan?.graph.nodes.length && !selectedNodeId) {
      setSelectedNodeId(flowOrder[0] ?? plan.graph.nodes[0]?.id ?? null);
    }
  }, [plan, flowOrder, selectedNodeId]);

  const onNodeClick = useCallback((_: MouseEvent, node: Node) => {
    setSelectedNodeId(node.id);
  }, []);

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
    },
    [setNodes],
  );

  if (!canGenerate) {
    return (
      <section className="arch-workspace arch-workspace--empty">
        <p>Complete the chat until status is <strong>sufficient</strong> or <strong>ready</strong>.</p>
        <button type="button" className="btn btn--ghost" onClick={onBackToSpec}>
          Back to specification
        </button>
      </section>
    );
  }

  if (!plan && !loading) {
    return (
      <section className="arch-workspace arch-workspace--empty">
        <div className="arch-workspace__intro">
          <h2>Generate your architecture</h2>
          <p>
            We will map your confirmed spec to the Affine agent catalog, decide
            reuse vs build per step, and draw an end-to-end flow.
          </p>
          <ul className="arch-workspace__bullets">
            <li>Left-to-right pipeline view</li>
            <li>Catalog agents matched per component</li>
            <li>Click any step for rationale</li>
          </ul>
        </div>
        {error ? <p className="chat-error">{error}</p> : null}
        <button
          type="button"
          className="btn btn--primary"
          disabled={loading}
          onClick={() => onGenerate(false)}
        >
          Generate architecture
        </button>
      </section>
    );
  }

  return (
    <section className="arch-workspace">
      <header className="arch-workspace__toolbar">
        <div className="arch-workspace__toolbar-left">
          <h2>System architecture</h2>
          {plan ? (
            <span className="arch-workspace__subtitle">
              {plan.graph.nodes.length} components · {plan.graph.edges.length}{" "}
              connections
              {plan.validation ? (
                <>
                  {" "}
                  ·{" "}
                  <span
                    className={`arch-validation__inline arch-validation__inline--${plan.validation.overall}`}
                  >
                    validation {plan.validation.overall}
                  </span>
                </>
              ) : null}
            </span>
          ) : null}
        </div>
        <div className="arch-workspace__toolbar-actions">
          <button type="button" className="btn btn--ghost" onClick={onBackToSpec}>
            Specification
          </button>
          <button
            type="button"
            className="btn btn--ghost"
            disabled={loading}
            onClick={() => onGenerate(true)}
          >
            {loading ? "Planning…" : "Regenerate"}
          </button>
        </div>
      </header>

      {error ? <p className="chat-error arch-workspace__error">{error}</p> : null}

      <div className="arch-workspace__body">
        <div className="arch-workspace__canvas-wrap">
          {loading && !plan ? (
            <div className="arch-workspace__loading">
              <span className="arch-workspace__spinner" aria-hidden />
              Planning architecture from spec and catalog…
            </div>
          ) : null}

          {plan ? (
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={onNodeClick}
              nodeTypes={nodeTypes}
              fitView
              fitViewOptions={{ padding: 0.35, maxZoom: 1 }}
              minZoom={0.15}
              maxZoom={1.25}
              nodesDraggable
              nodesConnectable={false}
              elementsSelectable
              proOptions={{ hideAttribution: true }}
              defaultEdgeOptions={{ type: "smoothstep" }}
            >
              <Background gap={20} size={1} color="#2a3347" />
              <Controls showInteractive={false} position="bottom-left" />
              <MiniMap
                position="bottom-right"
                pannable
                zoomable
                nodeColor={(n) => {
                  const d = n.data as { decision?: string; nodeType?: string };
                  if (d.nodeType === "human") return "#c4a574";
                  if (d.decision === "reuse") return "#3ecf8e";
                  if (d.decision === "adapt") return "#63b3ed";
                  return "#6b7a94";
                }}
              />
              <Panel position="top-left" className="arch-flow-hint">
                Flow → left to right
              </Panel>
            </ReactFlow>
          ) : null}
        </div>

        {plan ? (
          <ArchitectureInspector
            plan={plan}
            sessionId={sessionId}
            selectedNodeId={selectedNodeId}
            flowOrder={flowOrder}
            onSelectNode={focusNode}
            onPlanUpdated={onPlanUpdated}
            onRegenerate={() => onGenerate(true)}
          />
        ) : null}
      </div>
    </section>
  );
}
