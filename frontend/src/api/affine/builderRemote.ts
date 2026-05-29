import type { LaunchpadWorkflowEntry, SavedBuilderWorkflow } from "./builderStorage";
import { AffineApiError } from "./client";

const API_BASE = import.meta.env.VITE_AFFINE_API_BASE ?? "";

export async function fetchBuilderWorkflowRemote(
  sessionId: string,
): Promise<SavedBuilderWorkflow | null> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/builder`);
  if (res.status === 404) return null;
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail =
      (err as { detail?: string }).detail ??
      `Failed to load workflow (${res.status})`;
    throw new AffineApiError(detail, res.status);
  }
  const data = (await res.json()) as { workflow?: SavedBuilderWorkflow };
  const w = data.workflow;
  if (!w?.sessionId || !w?.plan) return null;
  return w as SavedBuilderWorkflow;
}

export async function saveBuilderWorkflowRemote(
  state: SavedBuilderWorkflow,
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/api/sessions/${state.sessionId}/builder`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state),
    },
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail =
      (err as { detail?: string }).detail ??
      `Failed to save workflow (${res.status})`;
    throw new AffineApiError(detail, res.status);
  }
}

export async function fetchLaunchpadWorkflowIndexRemote(): Promise<
  LaunchpadWorkflowEntry[] | null
> {
  const res = await fetch(`${API_BASE}/api/launchpad/workflows`);
  if (!res.ok) {
    return null;
  }
  const data = (await res.json()) as { workflows?: LaunchpadWorkflowEntry[] };
  return Array.isArray(data.workflows) ? data.workflows : [];
}
