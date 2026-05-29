import { Link, useRouterState } from "@tanstack/react-router";
import {
  LayoutDashboard,
  Workflow,
  LayoutTemplate,
  Boxes,
  Sparkles,
  MessageSquare,
} from "lucide-react";
import { Logo } from "./Logo";

const NAV = [
  { to: "/interview", label: "Agent Launchpad", icon: MessageSquare },
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/builder", label: "Workflow Builder", icon: Sparkles },
  { to: "/workflows", label: "Workflows", icon: Workflow },
  { to: "/templates", label: "Templates", icon: LayoutTemplate },
  { to: "/agents", label: "Agent Library", icon: Boxes },
] as const;

export function Sidebar() {
  const path = useRouterState({ select: (s) => s.location.pathname });
  return (
    <aside className="w-60 shrink-0 border-r border-border bg-surface flex flex-col h-screen sticky top-0">
      <div className="h-16 px-4 flex items-center border-b border-border">
        <Logo />
      </div>
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
        {NAV.map(({ to, label, icon: Icon }) => {
          const active = to === "/" ? path === "/" : path.startsWith(to);
          return (
            <Link
              key={to}
              to={to}
              className={[
                "flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors",
                active
                  ? "bg-primary/10 text-primary font-medium"
                  : "text-foreground/80 hover:bg-muted hover:text-foreground",
              ].join(" ")}
            >
              <Icon size={16} className={active ? "text-primary" : "text-muted-foreground"} />
              <span>{label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="px-4 py-3 border-t border-border text-[11px] text-muted-foreground">
        Affine Analytics — AgentForge v1.0
      </div>
    </aside>
  );
}
