import { useQuery } from "@tanstack/react-query";
import { fetchCatalogAgents } from "./affine/catalog";
import { apiFetch } from "./client";
import type {
  WorkflowSummary,
  Run,
  Template,
  RunsOverTimeEntry,
  AgentUsageEntry,
  DashboardStats,
} from "@/types/api";

const apiQueryOpts = {
  retry: 1,
  refetchOnWindowFocus: false,
  staleTime: 60 * 1000,
} as const;

export function useAgents() {
  return useQuery({
    queryKey: ["catalog-agents"],
    queryFn: fetchCatalogAgents,
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });
}

export function useTemplates() {
  return useQuery({
    queryKey: ["templates"],
    queryFn: () => apiFetch<Template[]>("/templates"),
    ...apiQueryOpts,
  });
}

export function useDashboardStats() {
  return useQuery({
    queryKey: ["dashboard", "stats"],
    queryFn: () => apiFetch<DashboardStats>("/dashboard/stats"),
    ...apiQueryOpts,
  });
}

export function useRunsOverTime() {
  return useQuery({
    queryKey: ["dashboard", "runs-over-time"],
    queryFn: () => apiFetch<RunsOverTimeEntry[]>("/dashboard/runs-over-time"),
    ...apiQueryOpts,
  });
}

export function useAgentUsage() {
  return useQuery({
    queryKey: ["dashboard", "agent-usage"],
    queryFn: () => apiFetch<AgentUsageEntry[]>("/dashboard/agent-usage"),
    ...apiQueryOpts,
  });
}

export function useRecentRuns() {
  return useQuery({
    queryKey: ["dashboard", "recent-runs"],
    queryFn: () => apiFetch<Run[]>("/dashboard/recent-runs"),
    ...apiQueryOpts,
  });
}

export function useTopWorkflows() {
  return useQuery({
    queryKey: ["dashboard", "top-workflows"],
    queryFn: () => apiFetch<WorkflowSummary[]>("/dashboard/top-workflows"),
    ...apiQueryOpts,
  });
}
