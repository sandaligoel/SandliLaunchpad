import { Bell, Search, HelpCircle } from "lucide-react";

export function Topbar({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: React.ReactNode }) {
  return (
    <header className="h-16 shrink-0 border-b border-border bg-surface px-6 flex items-center justify-between gap-4">
      <div>
        <h1 className="text-lg font-semibold leading-tight">{title}</h1>
        {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-2">
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-md border border-border bg-background w-72">
          <Search size={14} className="text-muted-foreground" />
          <input
            placeholder="Search workflows, agents, runs…"
            className="bg-transparent text-sm outline-none flex-1 placeholder:text-muted-foreground"
          />
        </div>
        {actions}
        <button className="h-9 w-9 grid place-items-center rounded-md border border-border bg-background hover:bg-muted">
          <HelpCircle size={16} className="text-muted-foreground" />
        </button>
        <button className="h-9 w-9 grid place-items-center rounded-md border border-border bg-background hover:bg-muted relative">
          <Bell size={16} className="text-muted-foreground" />
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-danger" />
        </button>
        <div className="h-9 w-9 rounded-full bg-primary text-primary-foreground grid place-items-center text-xs font-semibold">AR</div>
      </div>
    </header>
  );
}
