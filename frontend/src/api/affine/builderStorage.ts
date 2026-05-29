/**
 * Launchpad workflow persistence — backend / Azure Blob only (no browser localStorage).
 */

import {
  fetchBuilderWorkflowRemote,
  fetchLaunchpadWorkflowIndexRemote,
  saveBuilderWorkflowRemote,
} from "./builderRemote";
import type { ArchitecturePlan } from "./types";

export interface SavedBuilderWorkflow {
  sessionId: string;
  plan: ArchitecturePlan;
  nodePositions: Record<string, { x: number; y: number }>;
  selectedNodeId?: string | null;
  title?: string;
  problemStatement?: string;
  savedAt: string;
}

export interface LaunchpadWorkflowEntry {
  sessionId: string;
  title: string;
  savedAt: string;
  stepCount: number;
  agentCount: number;
  hasPlan: boolean;
}

function workflowHasPlan(entry: LaunchpadWorkflowEntry): boolean {
  return entry.hasPlan && entry.stepCount > 0;
}

/** @deprecated Use listLaunchpadWorkflowsAsync — local cache removed. */
export function listLaunchpadWorkflows(): LaunchpadWorkflowEntry[] {
  return [];
}

export async function listLaunchpadWorkflowsAsync(): Promise<
  LaunchpadWorkflowEntry[]
> {
  const remote = await fetchLaunchpadWorkflowIndexRemote();
  if (remote === null) {
    throw new Error(
      "Cannot load workflows from the API. Check that the AFFINE backend is running.",
    );
  }
  return remote.filter(workflowHasPlan);
}

/** @deprecated Use loadBuilderWorkflowAsync — local cache removed. */
export function loadBuilderWorkflow(
  _sessionId: string,
): SavedBuilderWorkflow | null {
  return null;
}

export async function loadBuilderWorkflowAsync(
  sessionId: string,
): Promise<SavedBuilderWorkflow | null> {
  const remote = await fetchBuilderWorkflowRemote(sessionId);
  if (!remote) return null;
  return remote;
}

export function registerLaunchpadWorkflowPlaceholder(
  _sessionId: string,
  _problemStatement: string,
): void {
  /* Session + workflow rows are created on the backend when the interview saves. */
}

export function preserveSessionBeforeNewInterview(
  sessionId: string | null,
  problemStatement?: string,
): void {
  void preserveSessionBeforeNewInterviewAsync(sessionId, problemStatement);
}

export async function preserveSessionBeforeNewInterviewAsync(
  sessionId: string | null,
  _problemStatement?: string,
): Promise<void> {
  if (!sessionId) return;
  const saved = await loadBuilderWorkflowAsync(sessionId);
  if (saved?.plan?.graph?.nodes?.length) {
    await saveBuilderWorkflowAsync(saved);
  }
}

/** @deprecated Active builder session is carried in /builder?sessionId= */
export function setActiveBuilderSessionId(_sessionId: string): void {}

/** @deprecated Use URL search on /builder */
export function getActiveBuilderSessionId(): string | null {
  return null;
}

export async function resolveBuilderSessionIdAsync(
  urlSessionId?: string | null,
): Promise<string | undefined> {
  if (urlSessionId?.trim()) return urlSessionId.trim();
  const workflows = await listLaunchpadWorkflowsAsync();
  return workflows[0]?.sessionId;
}

/** @deprecated Use resolveBuilderSessionIdAsync */
export function resolveBuilderSessionId(
  urlSessionId?: string | null,
): string | undefined {
  return urlSessionId?.trim() || undefined;
}

export async function saveBuilderWorkflowAsync(
  state: SavedBuilderWorkflow,
): Promise<void> {
  const payload: SavedBuilderWorkflow = {
    ...state,
    savedAt: state.savedAt || new Date().toISOString(),
  };
  await saveBuilderWorkflowRemote(payload);
}

export function saveBuilderWorkflow(state: SavedBuilderWorkflow): void {
  void saveBuilderWorkflowAsync(state);
}

/** No-op — nothing stored in the browser. */
export function clearBuilderWorkflow(_sessionId: string): void {}

/** @deprecated */
export function clearAllBuilderWorkflows(): void {}

export function upsertLaunchpadWorkflowIndex(_state: SavedBuilderWorkflow): void {
  /* Index is maintained on the backend when workflows are saved. */
}
