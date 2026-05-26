import type { LaunchpadWorkflowEntry, SavedBuilderWorkflow } from "./builderStorage";
import { AffineApiError } from "./client";

const API_BASE = import.meta.env.VITE_AFFINE_API_BASE ?? "";

export async function fetchBuilderWorkflowRemote(
  sessionId: string,
): Promise<SavedBuilderWorkflow | null> {
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/builder`);
    if (res.status === 404) return null;
    if (!res.ok) return null;
    const data = (await res.json()) as { workflow?: SavedBuilderWorkflow };
    const w = data.workflow;
    if (!w?.plan?.graph) return null;
    return w as SavedBuilderWorkflow;
  } catch {
    return null;
  }
}

export async function saveBuilderWorkflowRemote(
  state: SavedBuilderWorkflow,
): Promise<void> {
  try {
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
        `Builder save failed (${res.status})`;
      throw new AffineApiError(detail, res.status);
    }
  } catch (err) {
    if (err instanceof AffineApiError) throw err;
    /* offline — localStorage still holds a copy */
  }
}

export async function fetchLaunchpadWorkflowIndexRemote(): Promise<
  LaunchpadWorkflowEntry[] | null
> {
  try {
    const res = await fetch(`${API_BASE}/api/workflows`);
    if (!res.ok) return null;
    const data = (await res.json()) as { workflows?: LaunchpadWorkflowEntry[] };
    return Array.isArray(data.workflows) ? data.workflows : [];
  } catch {
    return null;
  }
}
