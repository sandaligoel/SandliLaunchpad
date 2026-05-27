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

function cacheWorkflowLocally(state: SavedBuilderWorkflow): void {
  if (typeof window === "undefined") return;
  const payload = {
    ...state,
    savedAt: state.savedAt || new Date().toISOString(),
  };
  localStorage.setItem(key(state.sessionId), JSON.stringify(payload));
  setActiveBuilderSessionId(state.sessionId);
  upsertLaunchpadWorkflowIndex(payload);
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

function placeholderWorkflow(
  sessionId: string,
  problemStatement: string,
): SavedBuilderWorkflow {
  const title =
    problemStatement.trim().length > 72
      ? `${problemStatement.trim().slice(0, 72)}…`
      : problemStatement.trim() || `Launchpad workflow ${sessionId.slice(0, 8)}`;
  return {
    sessionId,
    title,
    problemStatement: problemStatement.trim(),
    savedAt: new Date().toISOString(),
    nodePositions: {},
    selectedNodeId: null,
    plan: {
      graph: { nodes: [], edges: [] },
      reuse_decisions: [],
      catalog_matches: [],
      summary_markdown: "",
      open_questions: [],
    },
  };
}

export function registerLaunchpadWorkflowPlaceholder(
  sessionId: string,
  problemStatement: string,
): void {
  void saveBuilderWorkflowAsync(
    placeholderWorkflow(sessionId, problemStatement),
  );
}

/** Persist current session to backend before starting a new interview. */
export function preserveSessionBeforeNewInterview(
  sessionId: string | null,
  problemStatement?: string,
): void {
  void preserveSessionBeforeNewInterviewAsync(sessionId, problemStatement);
}

export async function preserveSessionBeforeNewInterviewAsync(
  sessionId: string | null,
  problemStatement?: string,
): Promise<void> {
  if (!sessionId) return;
  const saved =
    (await loadBuilderWorkflowAsync(sessionId)) ??
    loadBuilderWorkflow(sessionId);
  if (saved?.plan?.graph) {
    await saveBuilderWorkflowAsync(saved);
  } else if (problemStatement?.trim()) {
    await saveBuilderWorkflowAsync(
      placeholderWorkflow(sessionId, problemStatement),
    );
  }
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

function mergeWorkflowIndexes(
  remote: LaunchpadWorkflowEntry[],
  local: LaunchpadWorkflowEntry[],
): LaunchpadWorkflowEntry[] {
  const byId = new Map<string, LaunchpadWorkflowEntry>();
  for (const entry of [...local, ...remote]) {
    const prev = byId.get(entry.sessionId);
    if (!prev) {
      byId.set(entry.sessionId, entry);
      continue;
    }
    const prevTime = prev.savedAt ? new Date(prev.savedAt).getTime() : 0;
    const nextTime = entry.savedAt ? new Date(entry.savedAt).getTime() : 0;
    if (nextTime >= prevTime) {
      byId.set(entry.sessionId, entry);
    }
  }
  return [...byId.values()].sort(
    (a, b) => new Date(b.savedAt).getTime() - new Date(a.savedAt).getTime(),
  );
}

export function listLaunchpadWorkflows(): LaunchpadWorkflowEntry[] {
  return listLaunchpadWorkflowsLocal();
}

/** Workflow list from Azure/backend first; local cache only if API is offline. */
export async function listLaunchpadWorkflowsAsync(): Promise<
  LaunchpadWorkflowEntry[]
> {
  const remote = await fetchLaunchpadWorkflowIndexRemote();
  if (remote !== null) {
    writeIndex(remote);
    return remote;
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

/** Load from backend first, then browser cache. */
export async function loadBuilderWorkflowAsync(
  sessionId: string,
): Promise<SavedBuilderWorkflow | null> {
  const remote = await fetchBuilderWorkflowRemote(sessionId);
  if (remote) {
    cacheWorkflowLocally(remote);
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

/** URL param → active builder → interview session → newest saved workflow. */
export function resolveBuilderSessionId(
  urlSessionId?: string | null,
): string | undefined {
  if (urlSessionId?.trim()) return urlSessionId.trim();
  const active = getActiveBuilderSessionId();
  if (active) return active;
  const fromInterview =
    typeof window !== "undefined"
      ? localStorage.getItem(SESSION_ID_STORAGE_KEY)
      : null;
  if (fromInterview) return fromInterview;
  const latest = listLaunchpadWorkflows()[0];
  return latest?.sessionId;
}

export async function resolveBuilderSessionIdAsync(
  urlSessionId?: string | null,
): Promise<string | undefined> {
  if (urlSessionId?.trim()) return urlSessionId.trim();
  const active = getActiveBuilderSessionId();
  if (active) return active;
  const fromInterview =
    typeof window !== "undefined"
      ? localStorage.getItem(SESSION_ID_STORAGE_KEY)
      : null;
  if (fromInterview) return fromInterview;
  const workflows = await listLaunchpadWorkflowsAsync();
  return workflows[0]?.sessionId;
}

/** Save to Azure/backend first, then cache in the browser. */
export async function saveBuilderWorkflowAsync(
  state: SavedBuilderWorkflow,
): Promise<void> {
  const payload: SavedBuilderWorkflow = {
    ...state,
    savedAt: state.savedAt || new Date().toISOString(),
  };
  await saveBuilderWorkflowRemote(payload);
  cacheWorkflowLocally(payload);
}

export function saveBuilderWorkflow(state: SavedBuilderWorkflow): void {
  void saveBuilderWorkflowAsync(state);
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
