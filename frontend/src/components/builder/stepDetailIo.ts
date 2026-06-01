export function prettyJson(obj: unknown): string {
  if (obj == null) return "{}";
  try {
    return JSON.stringify(obj, null, 2);
  } catch {
    return String(obj);
  }
}

export function parseJsonObject(
  text: string,
):
  | { ok: true; value: Record<string, unknown> }
  | { ok: false; error: string } {
  const trimmed = text.trim();
  if (!trimmed) {
    return { ok: false, error: "JSON cannot be empty" };
  }
  try {
    const parsed = JSON.parse(trimmed) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return { ok: false, error: "Must be a JSON object (not an array or primitive)" };
    }
    return { ok: true, value: parsed as Record<string, unknown> };
  } catch (e) {
    return {
      ok: false,
      error: e instanceof Error ? e.message : "Invalid JSON",
    };
  }
}

export function summarizeJsonEntries(
  json: Record<string, unknown> | null | undefined,
  emptyLabel = "No data for this step.",
): { key: string; preview: string }[] {
  if (!json || typeof json !== "object") {
    return [{ key: "", preview: emptyLabel }];
  }
  const entries = Object.entries(json);
  if (!entries.length) {
    return [{ key: "", preview: "Empty object" }];
  }
  return entries.map(([key, val]) => {
    let preview = "";
    if (val == null) preview = "null";
    else if (typeof val === "object") {
      const s = JSON.stringify(val);
      preview = s.length > 120 ? `${s.slice(0, 117)}…` : s;
    } else preview = String(val);
    return { key, preview };
  });
}
