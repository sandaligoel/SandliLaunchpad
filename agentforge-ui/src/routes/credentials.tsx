import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/layout/AppShell";
import { Topbar } from "@/components/layout/Topbar";
import { Card } from "@/components/af/Card";
import { Badge } from "@/components/af/Badge";
import { useCredentials } from "@/api/hooks";
import { Plus, KeyRound, Eye, EyeOff } from "lucide-react";
import { useState } from "react";

export const Route = createFileRoute("/credentials")({
  head: () => ({ meta: [{ title: "Credentials — AgentForge" }, { name: "description", content: "Securely manage credentials referenced by agents." }] }),
  component: Credentials,
});

function Credentials() {
  const { data: CREDENTIALS = [] } = useCredentials();
  const [revealed, setRevealed] = useState<Record<string, boolean>>({});
  return (
    <AppShell>
      <Topbar
        title="Credentials"
        subtitle="Securely referenced via env variables — values never leave your vault"
        actions={
          <button className="h-9 px-3 inline-flex items-center gap-1.5 text-[12.5px] rounded-md bg-primary text-primary-foreground hover:opacity-90">
            <Plus size={14} /> Add credential
          </button>
        }
      />
      <main className="p-6 overflow-auto">
        <Card>
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead className="text-[11px] uppercase tracking-wider text-muted-foreground bg-muted/50 sticky top-0">
                <tr>
                  <th className="text-left font-medium px-5 py-2.5">Name</th>
                  <th className="text-left font-medium px-3 py-2.5">Provider</th>
                  <th className="text-left font-medium px-3 py-2.5">Type</th>
                  <th className="text-left font-medium px-3 py-2.5">Value</th>
                  <th className="text-left font-medium px-3 py-2.5">Env Reference</th>
                  <th className="text-right font-medium px-5 py-2.5">Actions</th>
                </tr>
              </thead>
              <tbody>
                {CREDENTIALS.map((c, i) => (
                  <tr key={c.id} className={i % 2 ? "bg-muted/30" : ""}>
                    <td className="px-5 py-3 font-medium flex items-center gap-2"><KeyRound size={13} className="text-muted-foreground" /> {c.name}</td>
                    <td className="px-3 py-3"><Badge variant="info">{c.provider}</Badge></td>
                    <td className="px-3 py-3 text-muted-foreground">{c.type}</td>
                    <td className="px-3 py-3 font-mono text-[11.5px]">{revealed[c.id] ? c.masked.replace(/•+/g, "REDACTED-FOR-MOCK") : c.masked}</td>
                    <td className="px-3 py-3 font-mono text-[11.5px] text-secondary">{c.envRef}</td>
                    <td className="px-5 py-3 text-right">
                      <button onClick={() => setRevealed((r) => ({ ...r, [c.id]: !r[c.id] }))} className="h-7 w-7 inline-grid place-items-center rounded-md hover:bg-muted text-muted-foreground" title="Toggle reveal">
                        {revealed[c.id] ? <EyeOff size={13} /> : <Eye size={13} />}
                      </button>
                      <button className="ml-1 h-7 px-2 text-[11px] rounded-md border border-border hover:bg-muted">Test</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </main>
    </AppShell>
  );
}
