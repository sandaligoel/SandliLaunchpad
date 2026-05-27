export function Logo({ collapsed = false }: { collapsed?: boolean }) {
  return (
    <div className="flex items-center gap-2 select-none">
      <svg width="28" height="28" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="Affine Analytics logo">
        <rect width="32" height="32" rx="7" fill="var(--color-primary)" />
        <path d="M8 22L14 10L20 22" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M10.5 18H17.5" stroke="white" strokeWidth="2.2" strokeLinecap="round" />
        <circle cx="23" cy="11" r="2.4" fill="var(--color-accent)" />
      </svg>
      {!collapsed && (
        <div className="leading-tight">
          <div className="text-[15px] font-semibold text-primary tracking-tight">Affine Analytics</div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">AgentForge</div>
        </div>
      )}
    </div>
  );
}
