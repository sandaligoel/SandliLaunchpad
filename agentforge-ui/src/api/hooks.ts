import { useQuery } from "@tanstack/react-query";
import { fetchCatalogAgents } from "./affine/catalog";
import { apiFetch } from "./client";
import type {
  AgentDef,
  WorkflowSummary,
  Run,
  Credential,
  Template,
  DashboardStats,
  RunsOverTimeEntry,
  AgentUsageEntry,
} from "@/types/api";

export function useAgents() {
  return useQuery({
    queryKey: ["catalog-agents"],
    queryFn: fetchCatalogAgents,
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });
}

export function useWorkflows() {
  return useQuery({
    queryKey: ["workflows"],
    queryFn: () => apiFetch<WorkflowSummary[]>("/workflows"),
  });
}

export function useRuns(status?: string, q?: string) {
  const params = new URLSearchParams();
  if (status && status !== "all") params.set("status", status);
  if (q) params.set("q", q);
  const qs = params.toString();

  return useQuery({
    queryKey: ["runs", status, q],
    queryFn: () => apiFetch<Run[]>(`/runs${qs ? `?${qs}` : ""}`),
  });
}

export function useAllRuns() {
  return useQuery({
    queryKey: ["runs"],
    queryFn: () => apiFetch<Run[]>("/runs"),
  });
}

export function useCredentials() {
  return useQuery({
    queryKey: ["credentials"],
    queryFn: () => apiFetch<Credential[]>("/credentials"),
  });
}

export function useTemplates() {
  return useQuery({
    queryKey: ["templates"],
    queryFn: () => apiFetch<Template[]>("/templates"),
  });
}

export function useDashboardStats() {
  return useQuery({
    queryKey: ["dashboard", "stats"],
    queryFn: () => apiFetch<DashboardStats>("/dashboard/stats"),
  });
}

export function useRunsOverTime() {
  return useQuery({
    queryKey: ["dashboard", "runs-over-time"],
    queryFn: () => apiFetch<RunsOverTimeEntry[]>("/dashboard/runs-over-time"),
  });
}

export function useAgentUsage() {
  return useQuery({
    queryKey: ["dashboard", "agent-usage"],
    queryFn: () => apiFetch<AgentUsageEntry[]>("/dashboard/agent-usage"),
  });
}

export function useRecentRuns() {
  return useQuery({
    queryKey: ["dashboard", "recent-runs"],
    queryFn: () => apiFetch<Run[]>("/dashboard/recent-runs"),
  });
}

export function useTopWorkflows() {
  return useQuery({
    queryKey: ["dashboard", "top-workflows"],
    queryFn: () => apiFetch<WorkflowSummary[]>("/dashboard/top-workflows"),
  });
}
