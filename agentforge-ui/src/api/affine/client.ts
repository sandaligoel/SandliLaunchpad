import type { ArchitectureResponse, SessionResponse } from "./types";

const API_BASE = import.meta.env.VITE_AFFINE_API_BASE ?? "";

export class AffineApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "AffineApiError";
    this.status = status;
  }
}

export function isSessionNotFoundError(err: unknown): boolean {
  return (
    err instanceof AffineApiError &&
    err.status === 404 &&
    /session not found/i.test(err.message)
  );
}

async function parseError(res: Response): Promise<AffineApiError> {
  const err = await res.json().catch(() => ({}));
  const detail =
    (err as { detail?: string }).detail ?? `Request failed (${res.status})`;
  return new AffineApiError(detail, res.status);
}

export const SESSION_ID_STORAGE_KEY = "affine_launchpad_session_id";

export interface AffineHealthResponse {
  status: string;
  storage?: {
    backend?: string;
    account?: string;
    container?: string;
    reachable?: boolean;
    session_blob_count?: number;
    error?: string;
  };
}

export async function checkAffineHealth(): Promise<AffineHealthResponse> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    throw new AffineApiError(`Health check failed (${res.status})`, res.status);
  }
  return res.json() as Promise<AffineHealthResponse>;
}

export interface SessionSummary {
  id: string;
  status?: string | null;
  problem_statement: string;
  message_count: number;
  has_architecture_plan: boolean;
}

export async function listSessions(): Promise<SessionSummary[]> {
  const res = await fetch(`${API_BASE}/api/sessions`);
  if (!res.ok) throw await parseError(res);
  const data = (await res.json()) as { sessions?: SessionSummary[] };
  return Array.isArray(data.sessions) ? data.sessions : [];
}

export async function startSession(
  problemStatement: string,
): Promise<SessionResponse> {
  const res = await fetch(`${API_BASE}/api/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ problem_statement: problemStatement }),
  });
  if (!res.ok) throw await parseError(res);
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
  if (!res.ok) throw await parseError(res);
  return res.json();
}

export async function getSession(sessionId: string): Promise<SessionResponse> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`);
  if (!res.ok) throw await parseError(res);
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
  if (!res.ok) throw await parseError(res);
  return res.json();
}

export async function getArchitecture(
  sessionId: string,
): Promise<ArchitectureResponse> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/architecture`);
  if (!res.ok) throw await parseError(res);
  return res.json();
}

export async function approveArchitecture(
  sessionId: string,
): Promise<ArchitectureResponse> {
  const res = await fetch(
    `${API_BASE}/api/sessions/${sessionId}/architecture/approve`,
    { method: "POST" },
  );
  if (!res.ok) throw await parseError(res);
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
  if (!res.ok) throw await parseError(res);
  return res.json();
}
