import { Bot, Braces, Wrench } from "lucide-react";
import { kindBadgeStyle, type ImplementationKind } from "@/utils/agentKind";

const ORDER: ImplementationKind[] = ["agent", "function", "tool"];

const ICONS = {
  agent: Bot,
  function: Braces,
  tool: Wrench,
} as const;

export function ImplementationKindLegend({
  compact = false,
  theme = "light",
}: {
  compact?: boolean;
  theme?: "light" | "dark";
}) {
  const isDark = theme === "dark";

  return (
    <div
      className={
        compact
          ? "grid grid-cols-1 gap-1.5"
          : `flex flex-wrap items-center gap-2 rounded-lg border px-3 py-2.5 ${
              isDark
                ? "border-slate-600/60 bg-slate-900/80"
                : "border-border bg-background/90"
            }`
      }
    >
      {!compact ? (
        <span
          className={`text-[10px] font-bold uppercase tracking-widest mr-1 ${
            isDark ? "text-slate-400" : "text-muted-foreground"
          }`}
        >
          Step types
        </span>
      ) : null}
      {ORDER.map((kind) => {
        const Icon = ICONS[kind];
        const tone = isDark ? "canvas" : "sidebar";
        const styles = kindBadgeStyle(kind, tone);
        return (
          <span
            key={kind}
            className={`inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${
              compact ? "w-full justify-center" : ""
            }`}
            style={{
              color: styles.color,
              background: styles.background,
              borderColor: styles.borderColor,
            }}
          >
            <Icon size={13} strokeWidth={2.5} aria-hidden />
            {kind === "agent" ? "Agent" : kind === "function" ? "Function" : "Tool"}
          </span>
        );
      })}
    </div>
  );
}
