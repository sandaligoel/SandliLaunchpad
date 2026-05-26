import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/layout/AppShell";
import { Topbar } from "@/components/layout/Topbar";
import { Card } from "@/components/af/Card";
import { Badge } from "@/components/af/Badge";
import { useAllRuns } from "@/api/hooks";
import { useState, useMemo } from "react";
import { Search } from "lucide-react";

export const Route = createFileRoute("/runs")({
  head: () => ({ meta: [{ title: "Runs — AgentForge" }, { name: "description", content: "Execution history for all workflows." }] }),
  component: Runs,
});

function Runs() {
  const { data: RUNS = [] } = useAllRuns();
  const [status, setStatus] = useState<"all" | "success" | "failed" | "running">("all");
  const [q, setQ] = useState("");
  const rows = useMemo(() => RUNS.filter((r) => (status === "all" || r.status === status) && r.workflowName.toLowerCase().includes(q.toLowerCase())), [RUNS, status, q]);

  const [openId, setOpenId] = useState<string | null>(null);
  const open = openId ? RUNS.find((r) => r.id === openId)! : null;

  return (
    <AppShell>
      <Topbar title="Runs" subtitle={`${RUNS.length} total executions`} />
      <main className="p-6 overflow-auto">
        <Card>
          <div className="p-4 border-b border-border flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-md border border-border bg-background w-72">
              <Search size={13} className="text-muted-foreground" />
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search workflow…" className="bg-transparent text-sm outline-none flex-1" />
            </div>
            <div className="flex gap-1">
              {(["all", "success", "failed", "running"] as const).map((s) => (
                <button key={s} onClick={() => setStatus(s)} className={`px-2.5 py-1.5 text-[11.5px] rounded-md capitalize ${status === s ? "bg-primary text-primary-foreground" : "border border-border hover:bg-muted"}`}>
                  {s}
                </button>
              ))}
            </div>
          </div>
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead className="text-[11px] uppercase tracking-wider text-muted-foreground bg-muted/50 sticky top-0">
                <tr>
                  <th className="text-left font-medium px-5 py-2.5">Run ID</th>
                  <th className="text-left font-medium px-3 py-2.5">Workflow</th>
                  <th className="text-left font-medium px-3 py-2.5">Status</th>
                  <th className="text-right font-medium px-3 py-2.5">Started</th>
                  <th className="text-right font-medium px-3 py-2.5">Duration</th>
                  <th className="text-right font-medium px-3 py-2.5">Tokens</th>
                  <th className="text-right font-medium px-5 py-2.5">Cost</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={r.id} onClick={() => setOpenId(r.id)} className={`cursor-pointer hover:bg-muted/40 ${i % 2 ? "bg-muted/30" : ""}`}>
                    <td className="px-5 py-3 font-mono text-[12px]">{r.id}</td>
                    <td className="px-3 py-3">{r.workflowName}</td>
                    <td className="px-3 py-3"><Badge variant={r.status === "success" ? "success" : r.status === "failed" ? "danger" : "info"}>{r.status}</Badge></td>
                    <td className="px-3 py-3 text-right text-muted-foreground tabular-nums">{new Date(r.startedAt).toLocaleString()}</td>
                    <td className="px-3 py-3 text-right tabular-nums">{(r.durationMs / 1000).toFixed(2)}s</td>
                    <td className="px-3 py-3 text-right tabular-nums">{r.tokens.toLocaleString()}</td>
                    <td className="px-5 py-3 text-right tabular-nums">${r.cost.toFixed(4)}</td>
                  </tr>
                ))}
                {rows.length === 0 && <tr><td colSpan={7} className="text-center text-muted-foreground py-12">No runs match these filters.</td></tr>}
              </tbody>
            </table>
          </div>
        </Card>
      </main>

      {open && (
        <div className="fixed inset-0 z-50 bg-black/40 grid place-items-center p-6" onClick={() => setOpenId(null)}>
          <div className="bg-surface w-[760px] max-w-full max-h-[80vh] rounded-xl border border-border flex flex-col overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="px-5 py-3 border-b border-border flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold">{open.workflowName}</h3>
                <p className="text-[11px] text-muted-foreground font-mono">{open.id} · {(open.durationMs / 1000).toFixed(2)}s · {open.tokens.toLocaleString()} tokens</p>
              </div>
              <Badge variant={open.status === "success" ? "success" : open.status === "failed" ? "danger" : "info"}>{open.status}</Badge>
            </div>
            <div className="flex-1 overflow-auto p-5 space-y-3">
              {open.steps.map((s, idx) => (
                <div key={idx} className="border border-border rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] uppercase tracking-wider text-muted-foreground">Step {idx + 1}</span>
                      <span className="text-sm font-medium">{s.label}</span>
                      <Badge variant="muted">{s.agent}</Badge>
                    </div>
                    <span className="text-[11px] tabular-nums text-muted-foreground">{s.latencyMs} ms</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-[11px]">
                    <pre className="bg-background border border-border rounded p-2 overflow-auto font-mono">{JSON.stringify(s.input, null, 2)}</pre>
                    <pre className="bg-background border border-border rounded p-2 overflow-auto font-mono">{JSON.stringify(s.output, null, 2)}</pre>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
