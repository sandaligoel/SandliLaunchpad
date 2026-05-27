import {
  preserveSessionBeforeNewInterviewAsync,
  registerLaunchpadWorkflowPlaceholder,
} from "./builderStorage";
import { getSession, SESSION_ID_STORAGE_KEY } from "./client";

export function getStoredSessionId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(SESSION_ID_STORAGE_KEY);
}

export function setStoredSessionId(id: string): void {
  localStorage.setItem(SESSION_ID_STORAGE_KEY, id);
}

export function clearStoredSessionId(): void {
  localStorage.removeItem(SESSION_ID_STORAGE_KEY);
}

export function consumeFreshUrlFlag(): boolean {
  if (typeof window === "undefined") return false;
  const params = new URLSearchParams(window.location.search);
  const fresh = params.get("fresh");
  const wantsFresh =
    params.has("new") || fresh === "1" || fresh === "true";
  if (!wantsFresh) return false;
  const prevId = getStoredSessionId();
  void preserveSessionBeforeNewInterviewAsync(prevId).then(() => {
    if (prevId) {
      void getSession(prevId)
        .then(({ session }) =>
          registerLaunchpadWorkflowPlaceholder(
            prevId,
            session.spec.problem_statement,
          ),
        )
        .catch(() => {});
    }
  });
  clearStoredSessionId();
  params.delete("fresh");
  params.delete("new");
  const qs = params.toString();
  const next = `${window.location.pathname}${qs ? `?${qs}` : ""}${window.location.hash}`;
  window.history.replaceState(null, "", next);
  return true;
}
