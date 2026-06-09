import { Bot, Boxes, Braces, Hammer, RefreshCw, Wrench } from "lucide-react";
import type { ArchitecturePlan, ReuseDecision } from "@/api/affine/types";
import type { AgentDef } from "@/types/api";
import { ImplementationKindLegend } from "@/components/shared/ImplementationKindLegend";
import { ImplementationKindBadge } from "@/architecture-flow/components/nodes/shared";
import { KIND_META, classifyAgentDef, type ImplementationKind } from "@/utils/agentKind";
import { findAgentDef } from "@/utils/stepIo";

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
  catalogAgents,
  onSelect,
}: {
  decision: ReuseDecision;
  catalogAgents: AgentDef[];
  onSelect?: (nodeId: string) => void;
}) {
  const isReuse = decision.decision === "reuse" || decision.decision === "adapt";
  const catalog = findAgentDef(
    catalogAgents,
    decision.agent_id ?? null,
    decision.agent_name ?? decision.node_label,
  );
  const implKind: ImplementationKind | undefined = catalog
    ? catalog.implementationKind ?? classifyAgentDef(catalog)
    : undefined;
  const kindMeta = implKind ? KIND_META[implKind] : null;
  const KindIcon =
    implKind === "function" ? Braces : implKind === "tool" ? Wrench : implKind === "agent" ? Bot : null;

  return (
    <button
      type="button"
      onClick={() => onSelect?.(decision.node_id)}
      className="w-full text-left p-2.5 rounded-lg border border-border bg-background hover:bg-muted/40 transition"
      style={
        kindMeta
          ? { borderLeftWidth: 3, borderLeftColor: kindMeta.solid }
          : undefined
      }
    >
      <div className="flex items-start gap-2">
        <div
          className="w-8 h-8 rounded-md grid place-items-center shrink-0 text-white"
          style={{
            background: kindMeta
              ? kindMeta.solid
              : isReuse
                ? "var(--color-success)"
                : "var(--muted-foreground)",
          }}
        >
          {KindIcon ? <KindIcon size={16} strokeWidth={2.25} /> : isReuse ? <RefreshCw size={14} /> : <Hammer size={14} />}
        </div>
        <div className="min-w-0 flex-1">
          {implKind ? (
            <div className="mb-1.5">
              <ImplementationKindBadge kind={implKind} size="sm" tone="sidebar" />
            </div>
          ) : null}
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
  catalogAgents = [],
  onFocusNode,
}: {
  plan: ArchitecturePlan;
  catalogAgents?: AgentDef[];
  onFocusNode?: (nodeId: string) => void;
}) {
  const { reuse, build } = groupDecisions(plan);

  return (
    <aside className="launchpad-builder-sidebar w-64 shrink-0 border-r border-border bg-surface flex flex-col">
      <div className="px-4 py-3 border-b border-border">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
          <Boxes size={14} /> Workflow steps
        </h2>
        <p className="text-[10.5px] text-muted-foreground mt-1">
          {plan.graph.nodes.length} steps · {reuse.length} catalog · {build.length}{" "}
          build new
        </p>
        <div className="mt-3">
          <ImplementationKindLegend compact />
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        <section>
          <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[color:var(--color-success)] mb-2 flex items-center gap-1">
            <RefreshCw size={12} /> Catalog agents ({reuse.length})
          </h3>
          <div className="space-y-1.5">
            {reuse.length === 0 ? (
              <p className="text-[11px] text-muted-foreground px-1">
                No catalog agents in this plan yet.
              </p>
            ) : (
              reuse.map((d) => (
                <AgentRow
                  key={d.node_id}
                  decision={d}
                  catalogAgents={catalogAgents}
                  onSelect={onFocusNode}
                />
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
                All steps use catalog agents — nothing to build new.
              </p>
            ) : (
              build.map((d) => (
                <AgentRow
                  key={d.node_id}
                  decision={d}
                  catalogAgents={catalogAgents}
                  onSelect={onFocusNode}
                />
              ))
            )}
          </div>
        </section>
      </div>
    </aside>
  );
}
