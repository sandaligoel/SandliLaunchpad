/**
 * Interview session identity — URL is the only client-side pointer.
 * Conversation state lives on the backend (Azure Blob or server disk).
 */

import {
  preserveSessionBeforeNewInterviewAsync,
  registerLaunchpadWorkflowPlaceholder,
} from "./builderStorage";

export function getInterviewSessionIdFromUrl(): string | null {
  if (typeof window === "undefined") return null;
  const id = new URLSearchParams(window.location.search).get("sessionId");
  return id?.trim() || null;
}

/** Keep the active chat session in the address bar (shareable, refresh-safe). */
export function syncInterviewSessionToUrl(
  sessionId: string | null,
  replace = true,
): void {
  if (typeof window === "undefined") return;
  const params = new URLSearchParams(window.location.search);
  if (sessionId) {
    params.set("sessionId", sessionId);
  } else {
    params.delete("sessionId");
  }
  params.delete("fresh");
  params.delete("new");
  const qs = params.toString();
  const next = `${window.location.pathname}${qs ? `?${qs}` : ""}${window.location.hash}`;
  if (replace) {
    window.history.replaceState(null, "", next);
  } else {
    window.history.pushState(null, "", next);
  }
}

/**
 * `?fresh=1` or `?new` — preserve prior session to backend, then clear URL session.
 * Returns true when a fresh start was requested.
 */
export function consumeFreshUrlFlag(): boolean {
  if (typeof window === "undefined") return false;
  const params = new URLSearchParams(window.location.search);
  const fresh = params.get("fresh");
  const wantsFresh =
    params.has("new") || fresh === "1" || fresh === "true";
  if (!wantsFresh) return false;

  const prevId = getInterviewSessionIdFromUrl();
  void preserveSessionBeforeNewInterviewAsync(prevId).then(() => {
    if (prevId) {
      void import("./client").then(({ getSession }) =>
        getSession(prevId)
          .then(({ session }) =>
            registerLaunchpadWorkflowPlaceholder(
              prevId,
              session.spec.problem_statement,
            ),
          )
          .catch(() => {}),
      );
    }
  });

  syncInterviewSessionToUrl(null);
  return true;
}
