import { Boxes, Hammer, RefreshCw } from "lucide-react";
import type { ArchitecturePlan, ReuseDecision } from "@/api/affine/types";

function groupDecisions(plan: ArchitecturePlan) {
  const reuse: ReuseDecision[] = [];
  const build: ReuseDecision[] = [];
  for (const d of plan.reuse_decisions) {
    if (d.decision === "reuse" || d.decision === "adapt") {
      reuse.push(d);
    } else {
      build.push(d);
    }
  }
  return { reuse, build };
}

function AgentRow({
  decision,
  onSelect,
}: {
  decision: ReuseDecision;
  onSelect?: (nodeId: string) => void;
}) {
  const isReuse = decision.decision === "reuse" || decision.decision === "adapt";
  return (
    <button
      type="button"
      onClick={() => onSelect?.(decision.node_id)}
      className="w-full text-left p-2.5 rounded-lg border border-border bg-background hover:border-primary hover:bg-muted/50 transition"
    >
      <div className="flex items-start gap-2">
        <div
          className={`w-8 h-8 rounded-md grid place-items-center shrink-0 text-white ${isReuse ? "bg-[color:var(--color-success)]" : "bg-muted-foreground"}`}
        >
          {isReuse ? <RefreshCw size={14} /> : <Hammer size={14} />}
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[12.5px] font-medium leading-tight truncate">
            {decision.node_label}
          </div>
          {decision.agent_name ? (
            <div className="text-[10.5px] text-primary truncate">
              {decision.agent_name}
            </div>
          ) : (
            <div className="text-[10.5px] text-muted-foreground">
              {isReuse ? "Adapt from catalog" : "New component"}
            </div>
          )}
          <div className="text-[10px] text-muted-foreground mt-0.5 line-clamp-2">
            {decision.rationale}
          </div>
        </div>
      </div>
    </button>
  );
}

export function LaunchpadAgentPalette({
  plan,
  onFocusNode,
}: {
  plan: ArchitecturePlan;
  onFocusNode?: (nodeId: string) => void;
}) {
  const { reuse, build } = groupDecisions(plan);

  return (
    <aside className="w-64 shrink-0 border-r border-border bg-surface flex flex-col">
      <div className="px-4 py-3 border-b border-border">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
          <Boxes size={14} /> Launchpad agents
        </h2>
        <p className="text-[10.5px] text-muted-foreground mt-1">
          From your interview architecture
        </p>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        <section>
          <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[color:var(--color-success)] mb-2 flex items-center gap-1">
            <RefreshCw size={12} /> Reuse from catalog ({reuse.length})
          </h3>
          <div className="space-y-1.5">
            {reuse.length === 0 ? (
              <p className="text-[11px] text-muted-foreground px-1">
                No catalog reuse in this plan yet.
              </p>
            ) : (
              reuse.map((d) => (
                <AgentRow key={d.node_id} decision={d} onSelect={onFocusNode} />
              ))
            )}
          </div>
        </section>
        <section>
          <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1">
            <Hammer size={12} /> Build new ({build.length})
          </h3>
          <div className="space-y-1.5">
            {build.length === 0 ? (
              <p className="text-[11px] text-muted-foreground px-1">
                All steps map to existing catalog agents.
              </p>
            ) : (
              build.map((d) => (
                <AgentRow key={d.node_id} decision={d} onSelect={onFocusNode} />
              ))
            )}
          </div>
        </section>
      </div>
    </aside>
  );
}
