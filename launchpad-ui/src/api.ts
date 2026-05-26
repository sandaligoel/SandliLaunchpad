import type { ArchitectureResponse, SessionResponse } from "./types";

const API_BASE = "";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function isSessionNotFoundError(err: unknown): boolean {
  return (
    err instanceof ApiError &&
    err.status === 404 &&
    /session not found/i.test(err.message)
  );
}

async function parseError(res: Response): Promise<ApiError> {
  const err = await res.json().catch(() => ({}));
  const detail =
    (err as { detail?: string }).detail ?? `Request failed (${res.status})`;
  return new ApiError(detail, res.status);
}

export const SESSION_ID_STORAGE_KEY = "affine_launchpad_session_id";

export async function startSession(
  problemStatement: string,
): Promise<SessionResponse> {
  const res = await fetch(`${API_BASE}/api/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ problem_statement: problemStatement }),
  });
  if (!res.ok) {
    throw await parseError(res);
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
    throw await parseError(res);
  }
  return res.json();
}

export async function getSession(sessionId: string): Promise<SessionResponse> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`);
  if (!res.ok) {
    throw await parseError(res);
  }
  return res.json();
}

export async function generateArchitecture(
  sessionId: string,
  force = false,
): Promise<ArchitectureResponse> {
  const q = force ? "?force=true" : "";
  const res = await fetch(
    `${API_BASE}/api/sessions/${sessionId}/architecture${q}`,
    { method: "POST" },
  );
  if (!res.ok) {
    throw await parseError(res);
  }
  return res.json();
}

export async function getArchitecture(
  sessionId: string,
): Promise<ArchitectureResponse> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/architecture`);
  if (!res.ok) {
    throw await parseError(res);
  }
  return res.json();
}

export async function approveArchitecture(
  sessionId: string,
): Promise<ArchitectureResponse> {
  const res = await fetch(
    `${API_BASE}/api/sessions/${sessionId}/architecture/approve`,
    { method: "POST" },
  );
  if (!res.ok) {
    throw await parseError(res);
  }
  return res.json();
}

export async function applyRemediation(
  sessionId: string,
  findingId: string,
  optionId: string,
): Promise<ArchitectureResponse> {
  const res = await fetch(
    `${API_BASE}/api/sessions/${sessionId}/architecture/remediate`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ finding_id: findingId, option_id: optionId }),
    },
  );
  if (!res.ok) {
    throw await parseError(res);
  }
  return res.json();
}
