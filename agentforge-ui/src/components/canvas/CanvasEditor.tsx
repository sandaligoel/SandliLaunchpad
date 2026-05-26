import { ReactFlow, Background, Controls, MiniMap, type NodeTypes } from "@xyflow/react";
import { useCallback, useRef } from "react";
import { useWorkflowStore } from "@/store/workflowStore";
import { AgentNodeView } from "./AgentNode";
import type { AgentType } from "@/types/api";

const nodeTypes: NodeTypes = { agent: AgentNodeView as never };

export function CanvasEditor() {
  const { nodes, edges, onNodesChange, onEdgesChange, onConnect, addAgent, selectNode } = useWorkflowStore();
  const wrapperRef = useRef<HTMLDivElement>(null);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const type = e.dataTransfer.getData("application/agent-type") as AgentType;
      if (!type || !wrapperRef.current) return;
      const bounds = wrapperRef.current.getBoundingClientRect();
      addAgent(type, { x: e.clientX - bounds.left - 100, y: e.clientY - bounds.top - 30 });
    },
    [addAgent]
  );

  return (
    <div ref={wrapperRef} className="flex-1 min-w-0 relative bg-background" onDragOver={(e) => e.preventDefault()} onDrop={onDrop}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={(_, n) => selectNode(n.id)}
        onPaneClick={() => selectNode(null)}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={18} size={1} color="#E5E7EB" />
        <MiniMap pannable zoomable className="!bg-surface !border !border-border" nodeColor={(n) => {
          const data = n.data as { agent?: string };
          const map: Record<string, string> = {
            transformer: "#F39C12", retrieval: "#2E86C1", sql: "#16A085", evaluation: "#8E44AD",
            router: "#E67E22", tool: "#3498DB", memory: "#C0392B", api: "#2C3E50",
          };
          return map[data.agent ?? ""] ?? "#1B5E8C";
        }} />
        <Controls className="!bg-surface !border-border [&_button]:!bg-surface [&_button]:!border-border" />
      </ReactFlow>
    </div>
  );
}
