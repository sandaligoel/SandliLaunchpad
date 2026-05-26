import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/layout/AppShell";
import { Topbar } from "@/components/layout/Topbar";
import { Card, CardHeader } from "@/components/af/Card";

export const Route = createFileRoute("/settings")({
  head: () => ({ meta: [{ title: "Settings — AgentForge" }, { name: "description", content: "Workspace settings." }] }),
  component: Settings,
});

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <label className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">{label}</label>
      <input defaultValue={value} className="mt-1 w-full text-sm bg-background border border-border rounded-md px-3 py-2 outline-none focus:ring-2 ring-primary/30" />
    </div>
  );
}

function Settings() {
  return (
    <AppShell>
      <Topbar title="Settings" subtitle="Workspace preferences and API configuration" />
      <main className="p-6 overflow-auto space-y-4 max-w-3xl">
        <Card>
          <CardHeader title="Profile" subtitle="Your account information" />
          <div className="px-5 pb-5 grid grid-cols-2 gap-4">
            <Field label="Name" value="Anika Rao" />
            <Field label="Email" value="anika.rao@affineanalytics.com" />
            <Field label="Role" value="AI Engineer" />
            <Field label="Team" value="Platform AI" />
          </div>
        </Card>
        <Card>
          <CardHeader title="Backend" subtitle="API endpoint for workflow execution" />
          <div className="px-5 pb-5 grid grid-cols-1 gap-4">
            <Field label="API Base URL" value="https://api.agentforge.affine.local/v1" />
            <Field label="Default model" value="gpt-4o-mini" />
          </div>
        </Card>
        <Card>
          <CardHeader title="Export Preferences" subtitle="Format options for workflow exports" />
          <div className="px-5 pb-5 space-y-2 text-sm">
            <label className="flex items-center gap-2"><input type="checkbox" defaultChecked /> Include backend config payload</label>
            <label className="flex items-center gap-2"><input type="checkbox" defaultChecked /> Include deployment metadata</label>
            <label className="flex items-center gap-2"><input type="checkbox" /> Pretty-print JSON</label>
          </div>
        </Card>
      </main>
    </AppShell>
  );
}
