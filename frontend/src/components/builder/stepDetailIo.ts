export function prettyJson(obj: unknown): string {
  if (obj == null) return "—";
  try {
    return JSON.stringify(obj, null, 2);
  } catch {
    return String(obj);
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
