import type { SessionResponse } from "./types";

const API_BASE = "";

export async function startSession(
  problemStatement: string,
): Promise<SessionResponse> {
  const res = await fetch(`${API_BASE}/api/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ problem_statement: problemStatement }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      (err as { detail?: string }).detail ?? `Start failed (${res.status})`,
    );
  }
  return res.json();
}

export async function submitTurn(
  sessionId: string,
  answer: string,
): Promise<SessionResponse> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/turn`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      (err as { detail?: string }).detail ?? `Turn failed (${res.status})`,
    );
  }
  return res.json();
}

export async function getSession(sessionId: string): Promise<SessionResponse> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`);
  if (!res.ok) {
    throw new Error(`Session not found (${res.status})`);
  }
  return res.json();
}
