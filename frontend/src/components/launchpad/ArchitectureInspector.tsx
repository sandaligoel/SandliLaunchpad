import { useState } from "react";
import type { ArchitecturePlan, ReuseDecision } from "@/api/affine/types";
import { ArchitectureValidationPanel } from "./ArchitectureValidationPanel";

type InspectorTab = "flow" | "validation";

interface Props {
  plan: ArchitecturePlan;
  sessionId: string;
  selectedNodeId: string | null;
  flowOrder: string[];
  onSelectNode: (nodeId: string) => void;
  onPlanUpdated: (plan: ArchitecturePlan) => void;
  onRegenerate?: () => void;
}

function findDecision(
  decisions: ReuseDecision[],
  nodeId: string,
): ReuseDecision | undefined {
  return decisions.find((d) => d.node_id === nodeId);
}

export function ArchitectureInspector({
  plan,
  sessionId,
  selectedNodeId,
  flowOrder,
  onSelectNode,
  onPlanUpdated,
  onRegenerate,
}: Props) {
  const [tab, setTab] = useState<InspectorTab>(
    plan.validation?.fail_count ? "validation" : "flow",
  );

  const { graph, reuse_decisions: decisions } = plan;
  const nodeById = new Map(graph.nodes.map((n) => [n.id, n]));

  const counts = {
    reuse: decisions.filter((d) => d.decision === "reuse").length,
    adapt: decisions.filter((d) => d.decision === "adapt").length,
    build: decisions.filter((d) => d.decision === "build").length,
  };

  const selected = selectedNodeId ? nodeById.get(selectedNodeId) : null;
  const selectedDecision = selectedNodeId
    ? findDecision(decisions, selectedNodeId)
    : undefined;

  const v = plan.validation;

  return (
    <aside className="arch-inspector">
      <nav className="arch-inspector__tabs" aria-label="Inspector views">
        <button
          type="button"
          className={`arch-inspector__tab ${tab === "flow" ? "arch-inspector__tab--active" : ""}`}
          onClick={() => setTab("flow")}
        >
          Flow
        </button>
        <button
          type="button"
          className={`arch-inspector__tab ${tab === "validation" ? "arch-inspector__tab--active" : ""}`}
          onClick={() => setTab("validation")}
        >
          Validation
          {v ? (
            <span
              className={`arch-inspector__tab-badge arch-inspector__tab-badge--${v.overall}`}
            >
              {v.fail_count > 0 ? v.fail_count : v.warn_count}
            </span>
          ) : null}
        </button>
      </nav>

      {tab === "validation" ? (
        <ArchitectureValidationPanel
          plan={plan}
          sessionId={sessionId}
          onSelectNode={onSelectNode}
          onPlanUpdated={onPlanUpdated}
          onRegenerate={onRegenerate}
        />
      ) : (
        <>
          <section className="arch-inspector__section">
            <h3>Legend</h3>
            <ul className="arch-legend">
              <li>
                <span className="arch-legend__swatch arch-legend__swatch--reuse" />
                Reuse catalog agent
              </li>
              <li>
                <span className="arch-legend__swatch arch-legend__swatch--adapt" />
                Adapt existing agent
              </li>
              <li>
                <span className="arch-legend__swatch arch-legend__swatch--build" />
                Build new component
              </li>
              <li>
                <span className="arch-legend__swatch arch-legend__swatch--human" />
                Human / HITL step
              </li>
              <li>
                <span className="arch-legend__swatch arch-legend__swatch--gateway" />
                Entry / routing
              </li>
            </ul>
          </section>

          <section className="arch-inspector__section">
            <h3>Overview</h3>
            <div className="arch-stats">
              <span className="arch-stat">{graph.nodes.length} steps</span>
              <span className="arch-stat arch-stat--reuse">{counts.reuse} reuse</span>
              <span className="arch-stat arch-stat--adapt">{counts.adapt} adapt</span>
              <span className="arch-stat arch-stat--build">{counts.build} build</span>
            </div>
            {v ? (
              <button
                type="button"
                className={`arch-validation__link arch-validation__link--${v.overall}`}
                onClick={() => setTab("validation")}
              >
                Validation: {v.overall} ({v.fail_count} fail, {v.warn_count} warn)
              </button>
            ) : null}
          </section>

          <section className="arch-inspector__section arch-inspector__section--flow">
            <h3>Flow order</h3>
            <ol className="arch-flow-list">
              {flowOrder.map((id, index) => {
                const node = nodeById.get(id);
                if (!node) return null;
                const dec = findDecision(decisions, id);
                const isSelected = id === selectedNodeId;
                const vStatus = v?.node_status[id];
                return (
                  <li key={id}>
                    <button
                      type="button"
                      className={`arch-flow-list__btn ${isSelected ? "arch-flow-list__btn--active" : ""} ${vStatus && vStatus !== "pass" ? `arch-flow-list__btn--${vStatus}` : ""}`}
                      onClick={() => onSelectNode(id)}
                    >
                      {vStatus && vStatus !== "pass" ? (
                        <span
                          className={`arch-validation__dot arch-validation__dot--${vStatus}`}
                        />
                      ) : (
                        <span className="arch-flow-list__index">{index + 1}</span>
                      )}
                      <span className="arch-flow-list__body">
                        <span className="arch-flow-list__label">{node.label}</span>
                        <span
                          className={`arch-flow-list__tag arch-flow-list__tag--${dec?.decision ?? "build"}`}
                        >
                          {dec?.decision ?? node.type}
                        </span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ol>
          </section>

          {selected ? (
            <section className="arch-inspector__section arch-inspector__detail">
              <h3>Selected step</h3>
              <p className="arch-inspector__detail-title">{selected.label}</p>
              <dl className="arch-inspector__dl">
                <dt>Type</dt>
                <dd>{selected.type}</dd>
                <dt>Decision</dt>
                <dd>{selectedDecision?.decision ?? "—"}</dd>
                {selectedDecision?.agent_name ? (
                  <>
                    <dt>Catalog agent</dt>
                    <dd>{selectedDecision.agent_name}</dd>
                  </>
                ) : null}
                {selected.description ? (
                  <>
                    <dt>Description</dt>
                    <dd>{selected.description}</dd>
                  </>
                ) : null}
                {selectedDecision?.rationale ? (
                  <>
                    <dt>Rationale</dt>
                    <dd>{selectedDecision.rationale}</dd>
                  </>
                ) : null}
              </dl>
            </section>
          ) : (
            <p className="arch-inspector__hint">
              Click a node or flow step to see details.
            </p>
          )}
        </>
      )}
    </aside>
  );
}
