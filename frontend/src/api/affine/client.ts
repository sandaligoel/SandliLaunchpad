import type { ArchitectureResponse, SessionResponse } from "./types";

const API_BASE = import.meta.env.VITE_AFFINE_API_BASE ?? "";
const DIRECT_API_TARGET = (
  import.meta.env.VITE_AFFINE_API_TARGET ?? ""
).replace(/\/$/, "");
const REQUEST_TIMEOUT_MS = 20_000;
const INTERVIEW_TIMEOUT_MS = 180_000;
const HEALTH_TIMEOUT_MS = 12_000;
const HEALTH_RETRIES = 4;

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

async function fetchWithTimeout(
  input: RequestInfo | URL,
  init?: RequestInit,
  timeoutMs: number = REQUEST_TIMEOUT_MS,
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new AffineApiError(
        `Request timed out after ${Math.round(timeoutMs / 1000)}s`,
        408,
      );
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

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

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function healthUrls(): string[] {
  const urls = [`${API_BASE}/health`];
  if (
    DIRECT_API_TARGET &&
    !urls.some((u) => u === `${DIRECT_API_TARGET}/health`)
  ) {
    urls.push(`${DIRECT_API_TARGET}/health`);
  }
  return urls;
}

export async function checkAffineHealth(): Promise<AffineHealthResponse> {
  let last: unknown;
  const urls = healthUrls();
  for (let attempt = 0; attempt < HEALTH_RETRIES; attempt++) {
    for (const url of urls) {
      try {
        const res = await fetchWithTimeout(url, undefined, HEALTH_TIMEOUT_MS);
        if (!res.ok) {
          throw new AffineApiError(
            `Health check failed (${res.status})`,
            res.status,
          );
        }
        return res.json() as Promise<AffineHealthResponse>;
      } catch (err) {
        last = err;
      }
    }
    if (attempt < HEALTH_RETRIES - 1) {
      await sleep(800 * (attempt + 1));
    }
  }
  throw last instanceof Error ? last : new Error("Health check failed");
}

export interface SessionSummary {
  id: string;
  status?: string | null;
  problem_statement: string;
  message_count: number;
  has_architecture_plan: boolean;
}

export async function listSessions(): Promise<SessionSummary[]> {
  const res = await fetchWithTimeout(`${API_BASE}/api/sessions`);
  if (!res.ok) throw await parseError(res);
  const data = (await res.json()) as { sessions?: SessionSummary[] };
  return Array.isArray(data.sessions) ? data.sessions : [];
}

export async function startSession(
  problemStatement: string,
): Promise<SessionResponse> {
  const res = await fetchWithTimeout(`${API_BASE}/api/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ problem_statement: problemStatement }),
  }, INTERVIEW_TIMEOUT_MS);
  if (!res.ok) throw await parseError(res);
  return res.json();
}

export async function submitTurn(
  sessionId: string,
  answer: string,
): Promise<SessionResponse> {
  const res = await fetchWithTimeout(`${API_BASE}/api/sessions/${sessionId}/turn`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer }),
  }, INTERVIEW_TIMEOUT_MS);
  if (!res.ok) throw await parseError(res);
  return res.json();
}

export async function getSession(sessionId: string): Promise<SessionResponse> {
  const res = await fetchWithTimeout(
    `${API_BASE}/api/sessions/${sessionId}`,
    undefined,
    INTERVIEW_TIMEOUT_MS,
  );
  if (!res.ok) throw await parseError(res);
  return res.json();
}

export async function generateArchitecture(
  sessionId: string,
  force = false,
): Promise<ArchitectureResponse> {
  const q = force ? "?force=true" : "";
  const res = await fetchWithTimeout(
    `${API_BASE}/api/sessions/${sessionId}/architecture${q}`,
    { method: "POST" },
    INTERVIEW_TIMEOUT_MS,
  );
  if (!res.ok) throw await parseError(res);
  return res.json();
}

export async function getArchitecture(
  sessionId: string,
): Promise<ArchitectureResponse> {
  const res = await fetchWithTimeout(
    `${API_BASE}/api/sessions/${sessionId}/architecture`,
  );
  if (!res.ok) throw await parseError(res);
  return res.json();
}

export async function approveArchitecture(
  sessionId: string,
): Promise<ArchitectureResponse> {
  const res = await fetchWithTimeout(
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
  const res = await fetchWithTimeout(
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
