import { createFileRoute, Link } from "@tanstack/react-router";
import { AppShell } from "@/components/layout/AppShell";
import { Topbar } from "@/components/layout/Topbar";
import { Card } from "@/components/af/Card";
import { Badge } from "@/components/af/Badge";
import { useTemplates, useAgents } from "@/api/hooks";
import { ArrowRight, Sparkles } from "lucide-react";

export const Route = createFileRoute("/templates")({
  head: () => ({
    meta: [
      { title: "Templates — AgentForge" },
      { name: "description", content: "Prebuilt agent workflow templates." },
    ],
  }),
  component: Templates,
});

function Templates() {
  const { data: templates = [], isError } = useTemplates();
  const { data: agents = [] } = useAgents();

  return (
    <AppShell>
      <Topbar title="Templates" subtitle="Start from a prebuilt agent workflow" />
      <main className="p-6 overflow-auto">
        {isError ? (
          <p className="text-sm text-destructive mb-4">
            Could not load templates from the API. Ensure the AFFINE backend is
            running.
          </p>
        ) : null}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {templates.map((t) => (
            <Card key={t.id} className="p-5 flex flex-col">
              <div className="flex items-start justify-between">
                <div className="w-10 h-10 rounded-lg bg-primary/10 text-primary grid place-items-center">
                  <Sparkles size={18} />
                </div>
                <Badge variant="info">{t.category}</Badge>
              </div>
              <h3 className="mt-3 text-base font-semibold">{t.name}</h3>
              <p className="text-xs text-muted-foreground mt-1 flex-1">
                {t.description}
              </p>
              <div className="mt-4 flex flex-wrap gap-1.5">
                {t.agents.map((a, i) => {
                  const def = agents.find((x) => x.type === a);
                  if (!def) {
                    return (
                      <span
                        key={i}
                        className="text-[10.5px] font-medium px-2 py-0.5 rounded-full bg-muted text-muted-foreground"
                      >
                        {a}
                      </span>
                    );
                  }
                  return (
                    <span
                      key={i}
                      className="text-[10.5px] font-medium px-2 py-0.5 rounded-full text-white"
                      style={{ background: def.color }}
                    >
                      {def.name.replace(" Agent", "")}
                    </span>
                  );
                })}
              </div>
              <Link
                to="/interview"
                search={{ fresh: "1" }}
                className="mt-4 h-9 inline-flex items-center justify-center gap-1.5 text-[12.5px] rounded-md bg-primary text-primary-foreground hover:opacity-90"
              >
                Start from template <ArrowRight size={13} />
              </Link>
            </Card>
          ))}
        </div>
      </main>
    </AppShell>
  );
}
