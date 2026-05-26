type Variant = "default" | "success" | "warning" | "danger" | "info" | "muted" | "accent";

const styles: Record<Variant, string> = {
  default: "bg-primary/10 text-primary",
  success: "bg-[color:var(--color-success)]/12 text-[color:var(--color-success)]",
  warning: "bg-[color:var(--color-warning)]/15 text-[color:var(--color-warning)]",
  danger: "bg-[color:var(--color-danger)]/12 text-[color:var(--color-danger)]",
  info: "bg-secondary/12 text-secondary",
  muted: "bg-muted text-muted-foreground",
  accent: "bg-accent/15 text-[color:var(--color-accent)]",
};

export function Badge({ children, variant = "default" }: { children: React.ReactNode; variant?: Variant }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${styles[variant]}`}>
      {children}
    </span>
  );
}
