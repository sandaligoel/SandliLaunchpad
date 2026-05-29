import {
  ReactFlow,
  Background,
  BackgroundVariant,
  MiniMap,
  type EdgeTypes,
  type NodeTypes,
} from "@xyflow/react";
import { useCallback, useEffect, useRef } from "react";
import { useWorkflowStore } from "@/store/workflowStore";
import { AgentNodeView } from "./AgentNode";
import { FlowPipelineEdge } from "./FlowPipelineEdge";
import type { AgentType } from "@/types/api";
import { FitWorkflowView } from "@/components/canvas/FitWorkflowView";
import { PresentationFitEffect } from "@/components/canvas/PresentationFitEffect";
import { WorkflowCanvasControls } from "@/components/canvas/WorkflowCanvasControls";
import { useWorkflowPresentation } from "@/context/WorkflowPresentationContext";
import { useWorkflowFitAll } from "@/hooks/useWorkflowFitAll";
import {
  workflowDefaultEdgeOptions,
  workflowZoomConfig,
} from "@/utils/flowEdgeStyles";

const nodeTypes: NodeTypes = { agent: AgentNodeView as never };
const edgeTypes: EdgeTypes = { pipeline: FlowPipelineEdge };

export function CanvasEditor() {
  const {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addAgent,
    selectNode,
  } = useWorkflowStore();
  const wrapperRef = useRef<HTMLDivElement>(null);
  const presentation = useWorkflowPresentation();
  const isPresentation = presentation?.isPresentation ?? false;
  const onFitAll = useWorkflowFitAll();

  useEffect(() => {
    if (!isPresentation) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [isPresentation]);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const type = e.dataTransfer.getData("application/agent-type") as AgentType;
      if (!type || !wrapperRef.current) return;
      const bounds = wrapperRef.current.getBoundingClientRect();
      addAgent(type, {
        x: e.clientX - bounds.left - 100,
        y: e.clientY - bounds.top - 30,
      });
    },
    [addAgent],
  );

  return (
    <div
      ref={wrapperRef}
      className={
        isPresentation
          ? "workflow-canvas workflow-canvas--presentation fixed inset-0 z-[300]"
          : "workflow-canvas flex-1 min-h-0 relative"
      }
      onDragOver={(e) => e.preventDefault()}
      onDrop={onDrop}
    >
      <div className="absolute inset-0">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          defaultEdgeOptions={workflowDefaultEdgeOptions}
          connectionLineStyle={{
            stroke: "#6366f1",
            strokeWidth: 2.5,
            strokeLinecap: "round",
          }}
          defaultMarkerColor="#0d9488"
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={(_, n) => selectNode(n.id)}
          onPaneClick={() => selectNode(null)}
          snapToGrid
          nodesDraggable
          nodesConnectable
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
          <FitWorkflowView nodeCount={nodes.length} />
          <Background
            variant={BackgroundVariant.Dots}
            gap={22}
            size={1.25}
            color="#94a3b8"
            className="workflow-canvas-dots"
          />
          {!isPresentation ? (
            <MiniMap
              pannable
              zoomable
              className="!bg-surface !border !border-border !shadow-md"
              nodeColor={(n) => {
                const data = n.data as { agent?: string };
                const map: Record<string, string> = {
                  transformer: "#F39C12",
                  retrieval: "#2E86C1",
                  sql: "#16A085",
                  evaluation: "#8E44AD",
                  router: "#E67E22",
                  tool: "#3498DB",
                  memory: "#C0392B",
                  api: "#2C3E50",
                };
                return map[data.agent ?? ""] ?? "#1565a8";
              }}
            />
          ) : null}
        </ReactFlow>
      </div>
      <WorkflowCanvasControls onFitAll={onFitAll} />
    </div>
  );
}
