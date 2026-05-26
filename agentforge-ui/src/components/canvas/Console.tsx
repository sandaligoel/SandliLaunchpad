import { useMemo } from "react";
import { useWorkflowStore, validateWorkflow } from "@/store/workflowStore";
import { AlertTriangle, CheckCircle2, Info, Terminal } from "lucide-react";

export function Console() {
  const nodes = useWorkflowStore((s) => s.nodes);
  const edges = useWorkflowStore((s) => s.edges);
  const tab = useWorkflowStore((s) => s.consoleTab);
  const setTab = useWorkflowStore((s) => s.setConsoleTab);
  const selectNode = useWorkflowStore((s) => s.selectNode);

  const issues = useMemo(() => validateWorkflow(nodes, edges), [nodes, edges]);

  const order = useMemo(() => {
    // simple topological-ish order from edges
    const incoming = new Map<string, number>();
    nodes.forEach((n) => incoming.set(n.id, 0));
    edges.forEach((e) => incoming.set(e.target, (incoming.get(e.target) ?? 0) + 1));
    const sorted = [...nodes].sort((a, b) => (incoming.get(a.id)! - incoming.get(b.id)!));
    return sorted;
  }, [nodes, edges]);

  const schema = { name: useWorkflowStore.getState().name, version: useWorkflowStore.getState().version, nodes, edges };

  return (
    <div className="h-56 shrink-0 border-t border-border bg-surface flex flex-col">
      <div className="flex items-center gap-1 border-b border-border px-2">
        {(["validation", "logs", "preview", "schema"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-[11.5px] capitalize border-b-2 -mb-px ${
              tab === t ? "border-primary text-primary font-medium" : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {t === "schema" ? "JSON Schema" : t}
            {t === "validation" && issues.length > 0 && (
              <span className="ml-1.5 inline-flex items-center justify-center min-w-[16px] h-[16px] text-[10px] rounded-full bg-danger/12 text-[color:var(--color-danger)] px-1">
                {issues.length}
              </span>
            )}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-auto p-3 text-xs font-mono">
        {tab === "validation" && (
          <div className="space-y-1.5">
            {issues.length === 0 && (
              <div className="flex items-center gap-2 text-[color:var(--color-success)]">
                <CheckCircle2 size={14} /> All checks passed.
              </div>
            )}
            {issues.map((i, idx) => {
              const Icon = i.severity === "error" ? AlertTriangle : i.severity === "warning" ? AlertTriangle : Info;
              const color =
                i.severity === "error"
                  ? "text-[color:var(--color-danger)]"
                  : i.severity === "warning"
                  ? "text-[color:var(--color-warning)]"
                  : "text-secondary";
              return (
                <button
                  key={idx}
                  onClick={() => i.nodeId && selectNode(i.nodeId)}
                  className="w-full text-left flex items-start gap-2 p-1.5 rounded hover:bg-muted"
                >
                  <Icon size={13} className={`${color} mt-0.5`} />
                  <span><span className={`${color} uppercase text-[10px] mr-2`}>{i.severity}</span>{i.message}</span>
                </button>
              );
            })}
          </div>
        )}
        {tab === "logs" && (
          <div className="space-y-0.5 text-muted-foreground">
            <div><span className="text-secondary">[09:14:22]</span> workflow loaded · 4 nodes · 3 edges</div>
            <div><span className="text-secondary">[09:14:23]</span> validator ran · {issues.length} issue(s)</div>
            <div><span className="text-[color:var(--color-success)]">[09:14:24]</span> autosave OK</div>
            <div className="flex items-center gap-1.5"><Terminal size={11} /> Listening for changes…</div>
          </div>
        )}
        {tab === "preview" && (
          <ol className="space-y-1.5 list-decimal pl-5">
            {order.map((n) => (
              <li key={n.id}>
                <span className="text-foreground font-medium">{n.data.label}</span>{" "}
                <span className="text-muted-foreground">[{n.data.agent}]</span>
              </li>
            ))}
            {order.length === 0 && <div className="text-muted-foreground">No agents in workflow.</div>}
          </ol>
        )}
        {tab === "schema" && (
          <pre className="text-[11px] leading-relaxed">{JSON.stringify(schema, null, 2)}</pre>
        )}
      </div>
    </div>
  );
}
