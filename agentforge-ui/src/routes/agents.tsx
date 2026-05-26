import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Topbar } from "@/components/layout/Topbar";
import { Card } from "@/components/af/Card";
import { Badge } from "@/components/af/Badge";
import { useAgents } from "@/api/hooks";
import type { AgentDef } from "@/types/api";
import {
  Database,
  Table,
  Wand2,
  GitBranch,
  Wrench,
  Globe,
  Sparkles,
  X,
  Settings2,
  Search,
  Loader2,
} from "lucide-react";

const ICONS = {
  Database,
  Table,
  Wand2,
  GitBranch,
  Wrench,
  Globe,
  Sparkles,
  Cpu: Wrench,
  Building: Wrench,
  Cloud: Globe,
  Mail: Wrench,
  BarChart3: Table,
  Search,
  Video: Wrench,
  ImageIcon: Wrench,
} as const;

export const Route = createFileRoute("/agents")({
  head: () => ({
    meta: [
      { title: "Agent Library — AgentForge" },
      { name: "description", content: "Affine built agents from catalog." },
    ],
  }),
  component: Agents,
});

function Agents() {
  const { data: agents = [], isLoading, isError, error } = useAgents();
  const [active, setActive] = useState<AgentDef | null>(null);
  const [q, setQ] = useState("");

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return agents;
    return agents.filter(
      (a) =>
        a.name.toLowerCase().includes(needle) ||
        a.category.toLowerCase().includes(needle) ||
        a.description.toLowerCase().includes(needle) ||
        a.summary.toLowerCase().includes(needle),
    );
  }, [agents, q]);

  return (
    <AppShell>
      <Topbar
        title="Agent Library"
        subtitle={
          isLoading
            ? "Loading Affine catalog…"
            : `${agents.length} Affine built agents · click any card for details`
        }
      />
      <main className="p-6 overflow-auto space-y-4">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-md border border-border bg-background w-full max-w-md">
          <Search size={13} className="text-muted-foreground shrink-0" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search agents, category, client…"
            className="bg-transparent text-sm outline-none flex-1"
          />
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center gap-2 py-16 text-muted-foreground">
            <Loader2 className="animate-spin" size={20} />
            <span className="text-sm">Loading agents from spec.json…</span>
          </div>
        ) : isError ? (
          <div className="text-center py-16 text-sm text-destructive max-w-md mx-auto">
            Could not load catalog:{" "}
            {error instanceof Error ? error.message : "unknown error"}
            <p className="text-muted-foreground mt-2 text-xs">
              Start the AFFINE API (port in AFFINE_API_TARGET) and refresh.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filtered.map((a) => {
              const Icon = ICONS[a.icon as keyof typeof ICONS] ?? Wrench;
              return (
                <button
                  key={a.type}
                  onClick={() => setActive(a)}
                  className="text-left focus:outline-none focus:ring-2 ring-primary/40 rounded-lg"
                >
                  <Card className="overflow-hidden hover:shadow-md hover:border-primary/40 transition-all cursor-pointer h-full">
                    <div
                      className="px-4 py-3 flex items-center gap-2.5 text-white"
                      style={{ background: a.color }}
                    >
                      <Icon size={16} />
                      <h3 className="text-sm font-semibold flex-1">{a.name}</h3>
                      <Settings2 size={14} className="opacity-80" />
                    </div>
                    <div className="p-4 space-y-3">
                      <Badge variant="info">{a.category}</Badge>
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {a.description}
                      </p>
                      <div className="grid grid-cols-2 gap-2 text-[11px]">
                        <div>
                          <div className="text-muted-foreground uppercase tracking-wider">
                            Inputs
                          </div>
                          <div className="font-medium mt-0.5 line-clamp-2">
                            {a.inputs.join(", ")}
                          </div>
                        </div>
                        <div>
                          <div className="text-muted-foreground uppercase tracking-wider">
                            Outputs
                          </div>
                          <div className="font-medium mt-0.5 line-clamp-2">
                            {a.outputs.join(", ")}
                          </div>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {a.fields.slice(0, 4).map((f) => (
                          <Badge key={f.key} variant="muted">
                            {f.label}
                          </Badge>
                        ))}
                        {a.fields.length > 4 && (
                          <Badge variant="muted">+{a.fields.length - 4}</Badge>
                        )}
                      </div>
                    </div>
                  </Card>
                </button>
              );
            })}
            {filtered.length === 0 && (
              <p className="col-span-full text-center text-muted-foreground py-12">
                No agents match &quot;{q}&quot;.
              </p>
            )}
          </div>
        )}
      </main>
      {active && <CatalogDrawer agent={active} onClose={() => setActive(null)} />}
    </AppShell>
  );
}

/** Same drawer shell as before; catalog agents show read-only metadata. */
function CatalogDrawer({
  agent,
  onClose,
}: {
  agent: AgentDef;
  onClose: () => void;
}) {
  const Icon = ICONS[agent.icon as keyof typeof ICONS] ?? Wrench;

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/40" onClick={onClose} />
      <div className="w-full max-w-md bg-surface border-l border-border h-full flex flex-col shadow-2xl animate-in slide-in-from-right">
        <div
          className="px-4 py-3 flex items-center gap-2.5 text-white"
          style={{ background: agent.color }}
        >
          <Icon size={16} />
          <div className="flex-1 min-w-0">
            <div className="text-[10.5px] uppercase tracking-wider opacity-80">
              {agent.type}
            </div>
            <h3 className="text-sm font-semibold truncate">{agent.name}</h3>
          </div>
          <button
            onClick={onClose}
            className="h-8 w-8 grid place-items-center rounded-md hover:bg-white/15"
          >
            <X size={16} />
          </button>
        </div>
        <div className="px-4 py-3 border-b border-border">
          <p className="text-[11.5px] text-muted-foreground">{agent.description}</p>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          <div>
            <h4 className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold mb-3">
              Inputs
            </h4>
            <ul className="text-[12px] space-y-1 list-disc pl-4 text-foreground">
              {agent.inputs.map((i) => (
                <li key={i}>{i}</li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold mb-3">
              Outputs
            </h4>
            <ul className="text-[12px] space-y-1 list-disc pl-4 text-foreground">
              {agent.outputs.map((o) => (
                <li key={o}>{o}</li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold mb-3">
              Catalog details
            </h4>
            <dl className="space-y-2 text-[12px]">
              {agent.fields.map((f) => (
                <div key={f.key}>
                  <dt className="text-muted-foreground">{f.label}</dt>
                  <dd className="font-medium mt-0.5">{f.description}</dd>
                </div>
              ))}
            </dl>
          </div>
          {agent.summary && (
            <div className="p-3 rounded-lg bg-primary/5 border border-primary/15">
              <p className="text-[11.5px] text-primary leading-relaxed">
                {agent.summary}
              </p>
            </div>
          )}
        </div>
        <div className="px-4 py-3 border-t border-border flex justify-end">
          <button
            onClick={onClose}
            className="text-[12px] px-3 py-1.5 rounded-md bg-primary text-primary-foreground hover:opacity-90"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
