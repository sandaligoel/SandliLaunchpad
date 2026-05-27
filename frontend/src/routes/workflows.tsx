import { createFileRoute, Link } from "@tanstack/react-router";
import { AppShell } from "@/components/layout/AppShell";
import { Topbar } from "@/components/layout/Topbar";
import { Card } from "@/components/af/Card";
import { Badge } from "@/components/af/Badge";
import { listLaunchpadWorkflowsAsync } from "@/api/affine/builderStorage";
import type { LaunchpadWorkflowEntry } from "@/api/affine/builderStorage";
import { useEffect, useMemo, useState } from "react";
import { ArrowUpDown, Plus, Search } from "lucide-react";

export const Route = createFileRoute("/workflows")({
  head: () => ({
    meta: [
      { title: "Workflows — AgentForge" },
      {
        name: "description",
        content: "Agent Launchpad workflows saved to your workspace.",
      },
    ],
  }),
  component: Workflows,
});

type WorkflowRow = {
  sessionId: string;
  name: string;
  description: string;
  agentCount: number;
  lastRun: string;
  hasPlan: boolean;
};

function Workflows() {
  const [launchpadRows, setLaunchpadRows] = useState<LaunchpadWorkflowEntry[]>(
    [],
  );
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listLaunchpadWorkflowsAsync()
      .then((rows) => {
        if (!cancelled) setLaunchpadRows(rows);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const [q, setQ] = useState("");
  const [sortKey, setSortKey] = useState<"name" | "lastRun">("lastRun");

  const rows = useMemo((): WorkflowRow[] => {
    const mapped: WorkflowRow[] = launchpadRows.map((w) => ({
      sessionId: w.sessionId,
      name: w.title,
      description: w.hasPlan
        ? `${w.stepCount} steps · architecture on canvas`
        : "Interview saved — open to generate or edit architecture",
      agentCount: w.agentCount || w.stepCount,
      lastRun: w.savedAt,
      hasPlan: w.hasPlan,
    }));

    const filtered = mapped.filter((w) =>
      w.name.toLowerCase().includes(q.toLowerCase()),
    );

    return [...filtered].sort((a, b) => {
      if (sortKey === "name") return a.name.localeCompare(b.name);
      return new Date(b.lastRun).getTime() - new Date(a.lastRun).getTime();
    });
  }, [launchpadRows, q, sortKey]);

  return (
    <AppShell>
      <Topbar
        title="Workflows"
        subtitle={
          loading
            ? "Loading from workspace…"
            : `${launchpadRows.length} Agent Launchpad workflow${launchpadRows.length === 1 ? "" : "s"}`
        }
        actions={
          <Link
            to="/interview"
            search={{ fresh: "1" }}
            className="h-9 px-3 inline-flex items-center gap-1.5 text-[12.5px] rounded-md bg-primary text-primary-foreground hover:opacity-90"
          >
            <Plus size={14} /> New interview
          </Link>
        }
      />
      <main className="p-6 overflow-auto">
        <p className="text-xs text-muted-foreground mb-3">
          Saved from Agent Launchpad (Azure). Open a row to continue in the
          workflow builder.
        </p>
        <Card>
          <div className="p-4 border-b border-border flex items-center gap-2">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-md border border-border bg-background w-72">
              <Search size={13} className="text-muted-foreground" />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search launchpad workflows…"
                className="bg-transparent text-sm outline-none flex-1"
              />
            </div>
            <select
              value={sortKey}
              onChange={(e) => setSortKey(e.target.value as never)}
              className="text-sm border border-border rounded-md px-2.5 py-1.5 bg-background"
            >
              <option value="lastRun">Sort: Last saved</option>
              <option value="name">Sort: Name</option>
            </select>
          </div>
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead className="text-[11px] uppercase tracking-wider text-muted-foreground bg-muted/50 sticky top-0">
                <tr>
                  <th className="text-left font-medium px-5 py-2.5">
                    <span className="inline-flex items-center gap-1">
                      Name <ArrowUpDown size={10} />
                    </span>
                  </th>
                  <th className="text-left font-medium px-3 py-2.5">Status</th>
                  <th className="text-right font-medium px-3 py-2.5">Steps</th>
                  <th className="text-right font-medium px-5 py-2.5">
                    Last saved
                  </th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td
                      colSpan={4}
                      className="text-center text-muted-foreground py-12"
                    >
                      Loading workflows…
                    </td>
                  </tr>
                ) : null}
                {!loading &&
                  rows.map((w, i) => (
                    <tr key={w.sessionId} className={i % 2 ? "bg-muted/30" : ""}>
                      <td className="px-5 py-3">
                        <Link
                          to="/builder"
                          search={{ sessionId: w.sessionId }}
                          className="font-medium hover:text-primary"
                        >
                          {w.name}
                        </Link>
                        <div className="text-[11px] text-muted-foreground">
                          {w.description}
                        </div>
                      </td>
                      <td className="px-3 py-3">
                        <Badge variant={w.hasPlan ? "success" : "warning"}>
                          {w.hasPlan ? "has plan" : "interview"}
                        </Badge>
                      </td>
                      <td className="px-3 py-3 text-right tabular-nums">
                        {w.agentCount}
                      </td>
                      <td className="px-5 py-3 text-right text-muted-foreground tabular-nums">
                        {w.lastRun
                          ? new Date(w.lastRun).toLocaleString()
                          : "—"}
                      </td>
                    </tr>
                  ))}
                {!loading && rows.length === 0 && (
                  <tr>
                    <td
                      colSpan={4}
                      className="text-center text-muted-foreground py-12"
                    >
                      {q ? (
                        <>No workflows match &quot;{q}&quot;.</>
                      ) : (
                        <>
                          No Launchpad workflows yet.{" "}
                          <Link
                            to="/interview"
                            search={{ fresh: "1" }}
                            className="text-primary underline"
                          >
                            Start an interview
                          </Link>
                          .
                        </>
                      )}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </main>
    </AppShell>
  );
}
