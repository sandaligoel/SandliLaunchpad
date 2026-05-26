import { createFileRoute, Link } from "@tanstack/react-router";
import { AppShell } from "@/components/layout/AppShell";
import { Topbar } from "@/components/layout/Topbar";
import { Card } from "@/components/af/Card";
import { Badge } from "@/components/af/Badge";
import { useWorkflows } from "@/api/hooks";
import { listLaunchpadWorkflowsAsync } from "@/api/affine/builderStorage";
import type { LaunchpadWorkflowEntry } from "@/api/affine/builderStorage";
import { useEffect, useMemo, useState } from "react";
import { ArrowUpDown, Plus, Search } from "lucide-react";

export const Route = createFileRoute("/workflows")({
  head: () => ({
    meta: [
      { title: "Workflows — AgentForge" },
      { name: "description", content: "All AI workflows in your workspace." },
    ],
  }),
  component: Workflows,
});

function Workflows() {
  const { data: MOCK_WORKFLOWS = [] } = useWorkflows();
  const [launchpadRows, setLaunchpadRows] = useState<LaunchpadWorkflowEntry[]>(
    [],
  );

  useEffect(() => {
    let cancelled = false;
    listLaunchpadWorkflowsAsync().then((rows) => {
      if (!cancelled) setLaunchpadRows(rows);
    });
    return () => {
      cancelled = true;
    };
  }, []);
  const [q, setQ] = useState("");
  const [sortKey, setSortKey] = useState<"name" | "lastRun" | "successRate">(
    "lastRun",
  );

  const rows = useMemo(() => {
    type Row = {
      id: string;
      name: string;
      description: string;
      status: "published" | "draft" | "archived";
      owner: string;
      agentCount: number;
      successRate: number;
      version: string;
      lastRun: string;
      isLaunchpad: boolean;
      sessionId?: string;
    };

    const launchpad: Row[] = launchpadRows.map((w) => ({
      id: w.sessionId,
      sessionId: w.sessionId,
      name: w.title,
      description: w.hasPlan
        ? `${w.stepCount} steps · saved from Agent Launchpad`
        : "Interview complete — open to build architecture",
      status: "draft" as const,
      owner: "You",
      agentCount: w.agentCount || w.stepCount,
      successRate: 0,
      version: "Launchpad",
      lastRun: w.savedAt,
      isLaunchpad: true,
    }));

    const mock: Row[] = MOCK_WORKFLOWS.map((w) => ({
      id: w.id,
      name: w.name,
      description: w.description,
      status: w.status,
      owner: w.owner,
      agentCount: w.agentCount,
      successRate: w.successRate,
      version: w.version,
      lastRun: w.lastRun,
      isLaunchpad: false,
    }));

    const combined = [...launchpad, ...mock];
    const filtered = combined.filter((w) =>
      w.name.toLowerCase().includes(q.toLowerCase()),
    );
    return [...filtered].sort((a, b) => {
      if (a.isLaunchpad !== b.isLaunchpad) return a.isLaunchpad ? -1 : 1;
      if (sortKey === "name") return a.name.localeCompare(b.name);
      if (sortKey === "successRate") return b.successRate - a.successRate;
      return new Date(b.lastRun).getTime() - new Date(a.lastRun).getTime();
    });
  }, [MOCK_WORKFLOWS, launchpadRows, q, sortKey]);

  return (
    <AppShell>
      <Topbar
        title="Workflows"
        subtitle={`${launchpadRows.length} launchpad · ${MOCK_WORKFLOWS.length} workspace`}
        actions={
          <Link
            to="/interview"
            search={{ fresh: "1" }}
            className="h-9 px-3 inline-flex items-center gap-1.5 text-[12.5px] rounded-md bg-primary text-primary-foreground hover:opacity-90"
          >
            <Plus size={14} /> New Workflow
          </Link>
        }
      />
      <main className="p-6 overflow-auto">
        {launchpadRows.length > 0 ? (
          <p className="text-xs text-muted-foreground mb-3">
            Launchpad workflows are kept when you start a new interview. Open
            any row to continue editing that flow.
          </p>
        ) : null}
        <Card>
          <div className="p-4 border-b border-border flex items-center gap-2">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-md border border-border bg-background w-72">
              <Search size={13} className="text-muted-foreground" />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search workflows…"
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
              <option value="successRate">Sort: Success rate</option>
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
                  <th className="text-left font-medium px-3 py-2.5">Owner</th>
                  <th className="text-right font-medium px-3 py-2.5">Agents</th>
                  <th className="text-right font-medium px-3 py-2.5">Success</th>
                  <th className="text-right font-medium px-3 py-2.5">Version</th>
                  <th className="text-right font-medium px-5 py-2.5">
                    Last saved
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((w, i) => (
                  <tr key={w.id} className={i % 2 ? "bg-muted/30" : ""}>
                    <td className="px-5 py-3">
                      {w.isLaunchpad && w.sessionId ? (
                        <Link
                          to="/builder"
                          search={{ sessionId: w.sessionId }}
                          className="font-medium hover:text-primary"
                        >
                          {w.name}
                        </Link>
                      ) : (
                        <Link
                          to="/builder"
                          className="font-medium hover:text-primary"
                        >
                          {w.name}
                        </Link>
                      )}
                      <div className="text-[11px] text-muted-foreground">
                        {w.description}
                      </div>
                    </td>
                    <td className="px-3 py-3">
                      <Badge
                        variant={
                          w.isLaunchpad
                            ? "warning"
                            : w.status === "published"
                              ? "success"
                              : w.status === "draft"
                                ? "warning"
                                : "muted"
                        }
                      >
                        {w.isLaunchpad ? "launchpad" : w.status}
                      </Badge>
                    </td>
                    <td className="px-3 py-3 text-muted-foreground">
                      {w.owner}
                    </td>
                    <td className="px-3 py-3 text-right tabular-nums">
                      {w.agentCount}
                    </td>
                    <td className="px-3 py-3 text-right tabular-nums">
                      {w.isLaunchpad ? "—" : `${Math.round(w.successRate * 100)}%`}
                    </td>
                    <td className="px-3 py-3 text-right">
                      <Badge variant="muted">{w.version}</Badge>
                    </td>
                    <td className="px-5 py-3 text-right text-muted-foreground tabular-nums">
                      {new Date(w.lastRun).toLocaleString()}
                    </td>
                  </tr>
                ))}
                {rows.length === 0 && (
                  <tr>
                    <td
                      colSpan={7}
                      className="text-center text-muted-foreground py-12"
                    >
                      No workflows match &quot;{q}&quot;.
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
