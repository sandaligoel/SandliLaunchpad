import { createFileRoute, Link } from "@tanstack/react-router";
import { AppShell } from "@/components/layout/AppShell";
import { Topbar } from "@/components/layout/Topbar";
import { Card, CardHeader } from "@/components/af/Card";
import { Badge } from "@/components/af/Badge";
import { useRecentRuns, useRunsOverTime, useAgentUsage, useTopWorkflows } from "@/api/hooks";
import { Activity, Workflow, Layers, Zap, Plus, ArrowUpRight } from "lucide-react";
import { ChartBox } from "@/components/af/ChartBox";
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, BarChart, Bar, Legend } from "recharts";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Dashboard — AgentForge | Affine Analytics" },
      { name: "description", content: "Visual AI agent workflow platform overview." },
    ],
  }),
  component: Dashboard,
});

const KPI = [
  { label: "Total Workflows", value: "24", icon: Workflow, delta: "+3 this week", variant: "default" as const },
  { label: "Active Agents", value: "147", icon: Layers, delta: "8 types", variant: "info" as const },
  { label: "Runs Today", value: "412", icon: Activity, delta: "+18% vs yesterday", variant: "success" as const },
  { label: "Avg Latency", value: "1.42s", icon: Zap, delta: "-90ms vs last week", variant: "accent" as const },
];

function Dashboard() {
  const { data: recent = [] } = useRecentRuns();
  const { data: runsOverTime = [] } = useRunsOverTime();
  const { data: agentUsage = [] } = useAgentUsage();
  const { data: topWorkflows = [] } = useTopWorkflows();
  return (
    <AppShell>
      <Topbar
        title="Dashboard"
        subtitle="Overview of your AI agent workflows and runs"
        actions={
          <>
            <Link
              to="/interview"
              search={{ fresh: "1" }}
              className="h-9 px-3 inline-flex items-center gap-1.5 text-[12.5px] rounded-md bg-primary text-primary-foreground hover:opacity-90"
            >
              <Plus size={14} /> Agent Launchpad
            </Link>
            <Link
              to="/builder"
              className="h-9 px-3 inline-flex items-center gap-1.5 text-[12.5px] rounded-md border border-border bg-background hover:bg-muted"
            >
              Workflow Builder
            </Link>
          </>
        }
      />
      <main className="p-6 space-y-6 overflow-auto">
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {KPI.map((k) => (
            <Card key={k.label} className="p-5">
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-xs text-muted-foreground">{k.label}</div>
                  <div className="text-2xl font-semibold mt-1">{k.value}</div>
                </div>
                <div className="w-9 h-9 rounded-md bg-primary/10 text-primary grid place-items-center">
                  <k.icon size={16} />
                </div>
              </div>
              <div className="mt-3"><Badge variant={k.variant}>{k.delta}</Badge></div>
            </Card>
          ))}
        </section>

        <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card className="lg:col-span-2">
            <CardHeader title="Runs over time" subtitle="Last 14 days" action={<Badge variant="success">97.2% success</Badge>} />
            <ChartBox>
              <LineChart data={runsOverTime}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #E5E7EB", fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Line type="monotone" dataKey="success" stroke="#1B5E8C" strokeWidth={2} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="failed" stroke="#E74C3C" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ChartBox>
          </Card>
          <Card>
            <CardHeader title="Agent usage" subtitle="By type" />
            <ChartBox className="h-64 px-2 pb-4">
              <BarChart data={agentUsage} layout="vertical" margin={{ left: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 10 }} width={80} />
                <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #E5E7EB", fontSize: 12 }} />
                <Bar dataKey="uses" fill="#2E86C1" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ChartBox>
          </Card>
        </section>

        <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card className="lg:col-span-2">
            <CardHeader title="Recent runs" action={<Link to="/runs" className="text-xs text-primary inline-flex items-center gap-1">View all <ArrowUpRight size={12} /></Link>} />
            <div className="overflow-auto">
              <table className="w-full text-sm">
                <thead className="text-[11px] uppercase tracking-wider text-muted-foreground bg-muted/50">
                  <tr>
                    <th className="text-left font-medium px-5 py-2">Run</th>
                    <th className="text-left font-medium px-3 py-2">Workflow</th>
                    <th className="text-left font-medium px-3 py-2">Status</th>
                    <th className="text-right font-medium px-3 py-2">Latency</th>
                    <th className="text-right font-medium px-5 py-2">Tokens</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.map((r, i) => (
                    <tr key={r.id} className={i % 2 ? "bg-muted/30" : ""}>
                      <td className="px-5 py-2.5 font-mono text-[12px]">{r.id}</td>
                      <td className="px-3 py-2.5">{r.workflowName}</td>
                      <td className="px-3 py-2.5">
                        <Badge variant={r.status === "success" ? "success" : r.status === "failed" ? "danger" : "info"}>{r.status}</Badge>
                      </td>
                      <td className="px-3 py-2.5 text-right tabular-nums">{(r.durationMs / 1000).toFixed(2)}s</td>
                      <td className="px-5 py-2.5 text-right tabular-nums">{r.tokens.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
          <Card>
            <CardHeader title="Top workflows" subtitle="By success rate" />
            <ul className="px-5 pb-5 space-y-2.5">
              {topWorkflows.map((w) => (
                <li key={w.id} className="flex items-center justify-between text-sm">
                  <div className="min-w-0">
                    <div className="font-medium truncate">{w.name}</div>
                    <div className="text-[11px] text-muted-foreground">{w.agentCount} agents · {w.version}</div>
                  </div>
                  <Badge variant="success">{Math.round(w.successRate * 100)}%</Badge>
                </li>
              ))}
            </ul>
          </Card>
        </section>
      </main>
    </AppShell>
  );
}
