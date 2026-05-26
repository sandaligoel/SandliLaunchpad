import {
  fetchBuilderWorkflowRemote,
  fetchLaunchpadWorkflowIndexRemote,
  saveBuilderWorkflowRemote,
} from "./builderRemote";
import { SESSION_ID_STORAGE_KEY } from "./client";
import type { ArchitecturePlan } from "./types";

const PREFIX = "affine_launchpad_builder_v1_";
const INDEX_KEY = "affine_launchpad_workflow_index_v1";
const ACTIVE_SESSION_KEY = "affine_launchpad_active_builder_session";

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

function key(sessionId: string): string {
  return `${PREFIX}${sessionId}`;
}

function readIndex(): LaunchpadWorkflowEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(INDEX_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as LaunchpadWorkflowEntry[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeIndex(entries: LaunchpadWorkflowEntry[]): void {
  localStorage.setItem(INDEX_KEY, JSON.stringify(entries));
}

function titleFromState(state: SavedBuilderWorkflow): string {
  const t =
    state.title?.trim() ||
    state.problemStatement?.trim() ||
    state.plan.summary_markdown?.slice(0, 80);
  if (t) {
    return t.length > 72 ? `${t.slice(0, 72)}…` : t;
  }
  return `Launchpad workflow ${state.sessionId.slice(0, 8)}`;
}

export function upsertLaunchpadWorkflowIndex(
  state: SavedBuilderWorkflow,
): void {
  const nodes = state.plan?.graph?.nodes ?? [];
  const entry: LaunchpadWorkflowEntry = {
    sessionId: state.sessionId,
    title: titleFromState(state),
    savedAt: state.savedAt || new Date().toISOString(),
    stepCount: nodes.length,
    agentCount: state.plan.reuse_decisions?.length ?? nodes.length,
    hasPlan: nodes.length > 0,
  };
  const rest = readIndex().filter((e) => e.sessionId !== state.sessionId);
  writeIndex([entry, ...rest]);
}

export function registerLaunchpadWorkflowPlaceholder(
  sessionId: string,
  problemStatement: string,
): void {
  const title =
    problemStatement.trim().length > 72
      ? `${problemStatement.trim().slice(0, 72)}…`
      : problemStatement.trim() || `Launchpad workflow ${sessionId.slice(0, 8)}`;
  const entry: LaunchpadWorkflowEntry = {
    sessionId,
    title,
    savedAt: new Date().toISOString(),
    stepCount: 0,
    agentCount: 0,
    hasPlan: false,
  };
  const rest = readIndex().filter((e) => e.sessionId !== sessionId);
  writeIndex([entry, ...rest]);
}

/** Keep the current session in the index before starting a new interview. */
export function preserveSessionBeforeNewInterview(
  sessionId: string | null,
  problemStatement?: string,
): void {
  if (!sessionId) return;
  const saved = loadBuilderWorkflow(sessionId);
  if (saved) {
    upsertLaunchpadWorkflowIndex(saved);
  } else if (problemStatement?.trim()) {
    registerLaunchpadWorkflowPlaceholder(sessionId, problemStatement);
  }
  // Archive only — never delete previous session builder data here.
  const active = getActiveBuilderSessionId();
  if (active === sessionId && typeof window !== "undefined") {
    localStorage.removeItem(ACTIVE_SESSION_KEY);
  }
}

function listLaunchpadWorkflowsLocal(): LaunchpadWorkflowEntry[] {
  const indexed = readIndex();
  const seen = new Set(indexed.map((e) => e.sessionId));

  if (typeof window !== "undefined") {
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (!k?.startsWith(PREFIX)) continue;
      const sessionId = k.slice(PREFIX.length);
      if (seen.has(sessionId)) continue;
      const saved = loadBuilderWorkflow(sessionId);
      if (saved) {
        upsertLaunchpadWorkflowIndex(saved);
        seen.add(sessionId);
      }
    }
  }

  return readIndex().sort(
    (a, b) => new Date(b.savedAt).getTime() - new Date(a.savedAt).getTime(),
  );
}

export function listLaunchpadWorkflows(): LaunchpadWorkflowEntry[] {
  return listLaunchpadWorkflowsLocal();
}

/** Workflow list from Azure Blob (via API), merged with local index. */
export async function listLaunchpadWorkflowsAsync(): Promise<
  LaunchpadWorkflowEntry[]
> {
  const remote = await fetchLaunchpadWorkflowIndexRemote();
  if (remote?.length) {
    writeIndex(remote);
    return remote.sort(
      (a, b) => new Date(b.savedAt).getTime() - new Date(a.savedAt).getTime(),
    );
  }
  return listLaunchpadWorkflowsLocal();
}

export function loadBuilderWorkflow(
  sessionId: string,
): SavedBuilderWorkflow | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(key(sessionId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as SavedBuilderWorkflow;
    if (parsed.sessionId !== sessionId || !parsed.plan?.graph) return null;
    return parsed;
  } catch {
    return null;
  }
}

/** Load from Azure (via API) first, then fall back to browser localStorage. */
export async function loadBuilderWorkflowAsync(
  sessionId: string,
): Promise<SavedBuilderWorkflow | null> {
  const remote = await fetchBuilderWorkflowRemote(sessionId);
  if (remote) {
    localStorage.setItem(key(sessionId), JSON.stringify(remote));
    upsertLaunchpadWorkflowIndex(remote);
    return remote;
  }
  return loadBuilderWorkflow(sessionId);
}

export function setActiveBuilderSessionId(sessionId: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(ACTIVE_SESSION_KEY, sessionId);
}

export function getActiveBuilderSessionId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACTIVE_SESSION_KEY);
}

/** URL param → last builder session → interview session → newest saved workflow. */
export function resolveBuilderSessionId(
  urlSessionId?: string | null,
): string | undefined {
  if (urlSessionId?.trim()) return urlSessionId.trim();
  const active = getActiveBuilderSessionId();
  if (active && loadBuilderWorkflow(active)) return active;
  if (active) return active;
  const fromInterview =
    typeof window !== "undefined"
      ? localStorage.getItem(SESSION_ID_STORAGE_KEY)
      : null;
  if (fromInterview) return fromInterview;
  const latest = listLaunchpadWorkflows()[0];
  return latest?.sessionId;
}

export function saveBuilderWorkflow(state: SavedBuilderWorkflow): void {
  const payload = {
    ...state,
    savedAt: state.savedAt || new Date().toISOString(),
  };
  localStorage.setItem(key(state.sessionId), JSON.stringify(payload));
  setActiveBuilderSessionId(state.sessionId);
  upsertLaunchpadWorkflowIndex(payload);
  void saveBuilderWorkflowRemote(payload);
}

export function clearBuilderWorkflow(sessionId: string): void {
  localStorage.removeItem(key(sessionId));
  writeIndex(readIndex().filter((e) => e.sessionId !== sessionId));
}

/** @deprecated Prefer preserving workflows; clears all saved launchpad data. */
export function clearAllBuilderWorkflows(): void {
  if (typeof window === "undefined") return;
  const toRemove: string[] = [];
  for (let i = 0; i < localStorage.length; i++) {
    const k = localStorage.key(i);
    if (k?.startsWith(PREFIX)) toRemove.push(k);
  }
  toRemove.forEach((k) => localStorage.removeItem(k));
  localStorage.removeItem(INDEX_KEY);
}
