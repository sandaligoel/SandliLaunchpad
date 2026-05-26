/** Empty string = same-origin; Vite proxies /api → mock server on 3001. */
const API_BASE = import.meta.env.VITE_API_URL ?? "";

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const base = API_BASE.replace(/\/$/, "");
  const prefix = base || "/api";
  const res = await fetch(`${prefix}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}
