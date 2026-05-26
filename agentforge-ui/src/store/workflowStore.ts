import { create } from "zustand";
import {
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
} from "@xyflow/react";
import { AGENT_REGISTRY } from "@/mocks/data";
import type { AgentType } from "@/types/api";

export interface AgentNodeData extends Record<string, unknown> {
  agent: AgentType;
  label: string;
  config: Record<string, unknown>;
  status?: "idle" | "valid" | "warning" | "error";
}

export type AgentNode = Node<AgentNodeData>;

interface WorkflowState {
  name: string;
  version: string;
  nodes: AgentNode[];
  edges: Edge[];
  selectedNodeId: string | null;
  dirty: boolean;
  consoleTab: "validation" | "logs" | "preview" | "schema";
  setName: (n: string) => void;
  onNodesChange: (c: NodeChange[]) => void;
  onEdgesChange: (c: EdgeChange[]) => void;
  onConnect: (c: Connection) => void;
  addAgent: (agent: AgentType, position: { x: number; y: number }) => void;
  selectNode: (id: string | null) => void;
  updateNodeConfig: (id: string, patch: Record<string, unknown>) => void;
  removeNode: (id: string) => void;
  setConsoleTab: (t: WorkflowState["consoleTab"]) => void;
  reset: () => void;
}

const cfg = (type: AgentType) => ({ ...AGENT_REGISTRY.find((a) => a.type === type)!.defaultConfig });
const seedNodes: AgentNode[] = [
  { id: "n1", type: "agent", position: { x: 40, y: 160 }, data: { agent: "query-transformer", label: "Query Transformer", config: cfg("query-transformer"), status: "valid" } },
  { id: "n2", type: "agent", position: { x: 290, y: 160 }, data: { agent: "retrieval", label: "Retrieval Agent", config: cfg("retrieval"), status: "valid" } },
  { id: "n3", type: "agent", position: { x: 540, y: 160 }, data: { agent: "answer-gen", label: "Answer Generation", config: cfg("answer-gen"), status: "valid" } },
  { id: "n4", type: "agent", position: { x: 790, y: 160 }, data: { agent: "sql-insight", label: "SQL Insight Agent", config: cfg("sql-insight"), status: "warning" } },
];
const seedEdges: Edge[] = [
  { id: "e1-2", source: "n1", target: "n2", animated: true },
  { id: "e2-3", source: "n2", target: "n3", animated: true },
  { id: "e3-4", source: "n3", target: "n4", animated: true },
];

let nodeCounter = 5;

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  name: "RAG Knowledge Base",
  version: "v1.4",
  nodes: seedNodes,
  edges: seedEdges,
  selectedNodeId: "n1",
  dirty: false,
  consoleTab: "validation",
  setName: (n) => set({ name: n, dirty: true }),
  onNodesChange: (c) => set({ nodes: applyNodeChanges(c, get().nodes) as AgentNode[], dirty: true }),
  onEdgesChange: (c) => set({ edges: applyEdgeChanges(c, get().edges), dirty: true }),
  onConnect: (c) => set({ edges: addEdge({ ...c, animated: true }, get().edges), dirty: true }),
  addAgent: (agent, position) => {
    const def = AGENT_REGISTRY.find((a) => a.type === agent)!;
    const id = `n${nodeCounter++}`;
    const node: AgentNode = {
      id,
      type: "agent",
      position,
      data: { agent, label: def.name, config: { ...def.defaultConfig }, status: "idle" },
    };
    set({ nodes: [...get().nodes, node], selectedNodeId: id, dirty: true });
  },
  selectNode: (id) => set({ selectedNodeId: id }),
  updateNodeConfig: (id, patch) =>
    set({
      nodes: get().nodes.map((n) =>
        n.id === id ? { ...n, data: { ...n.data, config: { ...n.data.config, ...patch }, status: "valid" } } : n
      ),
      dirty: true,
    }),
  removeNode: (id) =>
    set({
      nodes: get().nodes.filter((n) => n.id !== id),
      edges: get().edges.filter((e) => e.source !== id && e.target !== id),
      selectedNodeId: null,
      dirty: true,
    }),
  setConsoleTab: (t) => set({ consoleTab: t }),
  reset: () => set({ nodes: seedNodes, edges: seedEdges, dirty: false, selectedNodeId: "n1" }),
}));

// Validation
export interface ValidationIssue {
  severity: "error" | "warning" | "info";
  nodeId?: string;
  message: string;
}

export function validateWorkflow(nodes: AgentNode[], edges: Edge[]): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  const connected = new Set<string>();
  edges.forEach((e) => { connected.add(e.source); connected.add(e.target); });
  nodes.forEach((n) => {
    if (nodes.length > 1 && !connected.has(n.id)) {
      issues.push({ severity: "warning", nodeId: n.id, message: `${n.data.label} is not connected to the graph.` });
    }
    const def = AGENT_REGISTRY.find((a) => a.type === n.data.agent);
    def?.fields.forEach((f) => {
      if (!f.required) return;
      const v = (n.data.config as Record<string, unknown>)[f.key];
      const empty = v === undefined || v === null || v === "" || (Array.isArray(v) && v.length === 0);
      if (empty) {
        issues.push({ severity: "error", nodeId: n.id, message: `${n.data.label}: "${f.label}" is required.` });
      }
    });
  });
  if (nodes.length === 0) issues.push({ severity: "info", message: "Empty workflow — drag agents from the palette to start." });
  if (edges.length === 0 && nodes.length > 1) issues.push({ severity: "warning", message: "No connections defined between agents." });
  return issues;
}
