/** True when the chip means the user will type a custom answer (not submit the label). */
export function isCustomDescribeChip(chip: string): boolean {
  const t = chip.trim().toLowerCase();
  if (!t) return false;
  if (t.includes("other") && t.includes("describe")) return true;
  if (t === "other") return true;
  if (/^other\s*[\/\-–]/.test(t)) return true;
  return false;
}
