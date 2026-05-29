import { useState } from "react";
import { useWorkflowStore, validateWorkflow } from "@/store/workflowStore";
import { Save, Play, ShieldCheck, Download, Rocket, RotateCcw, X } from "lucide-react";
import { Badge } from "@/components/af/Badge";

export function BuilderToolbar() {
  const name = useWorkflowStore((s) => s.name);
  const version = useWorkflowStore((s) => s.version);
  const setName = useWorkflowStore((s) => s.setName);
  const dirty = useWorkflowStore((s) => s.dirty);
  const reset = useWorkflowStore((s) => s.reset);
  const nodes = useWorkflowStore((s) => s.nodes);
  const edges = useWorkflowStore((s) => s.edges);
  const setConsoleTab = useWorkflowStore((s) => s.setConsoleTab);
  const [exporting, setExporting] = useState(false);

  const issues = validateWorkflow(nodes, edges);

  const exportPayload = {
    workflowSchema: { name, version, nodes, edges },
    backendConfig: {
      pipeline: nodes.map((n) => ({ id: n.id, agent: n.data.agent, config: n.data.config })),
      transitions: edges.map((e) => ({ from: e.source, to: e.target })),
    },
    deployMeta: { name, version, createdAt: new Date().toISOString(), agentCount: nodes.length },
  };

  return (
    <>
      <div className="h-14 border-b border-border bg-surface px-4 flex items-center gap-3">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="text-sm font-semibold bg-transparent outline-none focus:bg-muted px-2 py-1 rounded-md min-w-[200px]"
        />
        <Badge variant="muted">{version}</Badge>
        {dirty ? <Badge variant="warning">Unsaved</Badge> : <Badge variant="success">Saved</Badge>}
        <span className="text-[11px] text-muted-foreground ml-1">{nodes.length} agents · {edges.length} edges</span>

        <div className="ml-auto flex items-center gap-1.5">
          <button onClick={reset} className="h-8 px-2.5 inline-flex items-center gap-1.5 text-[12px] rounded-md hover:bg-muted text-muted-foreground" title="Reset">
            <RotateCcw size={13} /> Reset
          </button>
          <button onClick={() => setConsoleTab("validation")} className="h-8 px-3 inline-flex items-center gap-1.5 text-[12px] rounded-md border border-border hover:bg-muted">
            <ShieldCheck size={13} /> Validate
            {issues.length > 0 && <span className="ml-1 text-[10px] text-[color:var(--color-danger)]">({issues.length})</span>}
          </button>
          <button className="h-8 px-3 inline-flex items-center gap-1.5 text-[12px] rounded-md border border-border hover:bg-muted">
            <Play size={13} /> Run Test
          </button>
          <button onClick={() => setExporting(true)} className="h-8 px-3 inline-flex items-center gap-1.5 text-[12px] rounded-md border border-border hover:bg-muted">
            <Download size={13} /> Export
          </button>
          <button className="h-8 px-3 inline-flex items-center gap-1.5 text-[12px] rounded-md bg-primary text-primary-foreground hover:opacity-90">
            <Save size={13} /> Save
          </button>
          <button className="h-8 px-3 inline-flex items-center gap-1.5 text-[12px] rounded-md bg-accent text-[color:var(--accent-foreground)] hover:opacity-90">
            <Rocket size={13} /> Deploy
          </button>
        </div>
      </div>

      {exporting && (
        <div className="fixed inset-0 z-50 bg-black/40 grid place-items-center p-6" onClick={() => setExporting(false)}>
          <div className="bg-surface w-[720px] max-w-full max-h-[80vh] rounded-xl border border-border flex flex-col overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="px-5 py-3 border-b border-border flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold">Export Workflow</h3>
                <p className="text-xs text-muted-foreground">Schema, backend config, and deployment metadata.</p>
              </div>
              <button onClick={() => setExporting(false)} className="h-8 w-8 grid place-items-center hover:bg-muted rounded-md"><X size={14} /></button>
            </div>
            <div className="flex-1 overflow-auto p-4">
              <pre className="text-[11px] bg-background p-3 rounded-md border border-border font-mono leading-relaxed">{JSON.stringify(exportPayload, null, 2)}</pre>
            </div>
            <div className="px-5 py-3 border-t border-border flex justify-end gap-2">
              <button onClick={() => setExporting(false)} className="h-8 px-3 text-[12px] rounded-md border border-border hover:bg-muted">Close</button>
              <button
                onClick={() => {
                  const blob = new Blob([JSON.stringify(exportPayload, null, 2)], { type: "application/json" });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url; a.download = `${name.replace(/\s+/g, "_")}.json`; a.click();
                  URL.revokeObjectURL(url);
                }}
                className="h-8 px-3 text-[12px] rounded-md bg-primary text-primary-foreground hover:opacity-90"
              >
                Download JSON
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
