import { useMemo, useState } from "react";
import { applyRemediation, approveArchitecture } from "../api";
import type {
  ArchitecturePlan,
  RemediationOption,
  ValidationFinding,
  ValidationLevel,
} from "../types";

interface Props {
  plan: ArchitecturePlan;
  sessionId: string;
  onSelectNode: (nodeId: string) => void;
  onPlanUpdated: (plan: ArchitecturePlan) => void;
  onRegenerate?: () => void;
}

type Filter = "all" | "fail" | "warn";

const LEVEL_LABEL: Record<ValidationLevel, string> = {
  pass: "Pass",
  warn: "Review",
  fail: "Fail",
};

function isActionable(item: ValidationFinding): boolean {
  return (
    (item.level === "warn" || item.level === "fail") &&
    !item.resolved &&
    item.code !== "validation_scope" &&
    (item.remediations?.length ?? 0) > 0
  );
}

function needsStructuralFix(item: ValidationFinding): boolean {
  return (
    item.level === "fail" &&
    !!item.blocks_approval &&
    !!item.resolved &&
    item.resolution?.action === "acknowledge"
  );
}

function FindingCard({
  item,
  sessionId,
  onSelectNode,
  onPlanUpdated,
  applyingKey,
  setApplyingKey,
  setRemediateError,
}: {
  item: ValidationFinding;
  sessionId: string;
  onSelectNode: (nodeId: string) => void;
  onPlanUpdated: (plan: ArchitecturePlan) => void;
  applyingKey: string | null;
  setApplyingKey: (key: string | null) => void;
  setRemediateError: (msg: string | null) => void;
}) {
  const fid = item.finding_id ?? item.finding_key ?? `${item.code}:${item.node_id ?? "_"}`;
  const showActions = isActionable(item) || needsStructuralFix(item);

  const handleChoice = async (opt: RemediationOption) => {
    const key = `${fid}:${opt.id}`;
    if (!fid || !opt.id) return;
    setApplyingKey(key);
    setRemediateError(null);
    try {
      const { plan } = await applyRemediation(sessionId, fid, opt.id);
      onPlanUpdated(plan);
    } catch (e) {
      setRemediateError(
        e instanceof Error ? e.message : "Failed to apply fix",
      );
    } finally {
      setApplyingKey(null);
    }
  };

  return (
    <li
      className={`arch-validation__item arch-validation__item--${item.level} ${item.resolved ? "arch-validation__item--resolved" : ""}`}
    >
      <div className="arch-validation__item-head">
        <span className="arch-validation__level">{LEVEL_LABEL[item.level]}</span>
        {item.node_id ? (
          <button
            type="button"
            className="arch-validation__node-link"
            onClick={() => onSelectNode(item.node_id!)}
          >
            Go to step
          </button>
        ) : null}
      </div>
      <p className="arch-validation__message">{item.message}</p>
      {item.help_text ? (
        <p className="arch-validation__help">{item.help_text}</p>
      ) : null}
      {needsStructuralFix(item) ? (
        <p className="arch-validation__blocked">
          Acknowledged, but structural failures still block approval until you
          apply a fix (not only review).
        </p>
      ) : null}
      {item.resolved && item.resolution ? (
        <p className="arch-validation__resolved">
          Applied: {item.resolution.label || item.resolution.action_id}
        </p>
      ) : null}
      {showActions && (item.remediations?.length ?? 0) > 0 ? (
        <div
          className="arch-validation__choices arch-validation__choices--inline"
          role="group"
          aria-label="Fix options"
        >
          {item.remediations!.map((opt) => {
            const key = `${fid}:${opt.id}`;
            const busy = applyingKey === key;
            const disabled = applyingKey !== null && !busy;
            return (
              <button
                key={opt.id}
                type="button"
                className="arch-validation__choice arch-validation__choice--chip"
                disabled={disabled || busy}
                onClick={() => handleChoice(opt)}
                title={opt.description ?? undefined}
              >
                {busy ? "Applying…" : opt.label}
              </button>
            );
          })}
        </div>
      ) : null}
    </li>
  );
}

export function ArchitectureValidationPanel({
  plan,
  sessionId,
  onSelectNode,
  onPlanUpdated,
  onRegenerate,
}: Props) {
  const [filter, setFilter] = useState<Filter>("all");
  const [applyingKey, setApplyingKey] = useState<string | null>(null);
  const [remediateError, setRemediateError] = useState<string | null>(null);
  const [approving, setApproving] = useState(false);

  const v = plan.validation;
  const actionable = useMemo(
    () => (v?.items ?? []).filter(isActionable),
    [v],
  );
  const resolvedCount = useMemo(
    () =>
      (v?.items ?? []).filter(
        (i) =>
          i.resolved ||
          (i.level === "pass" && i.code !== "validation_scope"),
      ).length,
    [v],
  );

  if (!v) {
    return (
      <p className="arch-inspector__hint">
        Validation runs when you generate architecture.
      </p>
    );
  }

  const filtered = actionable.filter((i) => {
    if (filter === "fail") return i.level === "fail";
    if (filter === "warn") return i.level === "warn";
    return true;
  });

  const graphIssues = filtered.filter((i) => !i.node_id);
  const byNode = new Map<string, ValidationFinding[]>();
  for (const item of filtered) {
    if (!item.node_id) continue;
    if (!byNode.has(item.node_id)) byNode.set(item.node_id, []);
    byNode.get(item.node_id)!.push(item);
  }

  const handleApprove = async () => {
    setApproving(true);
    setRemediateError(null);
    try {
      const { plan: p } = await approveArchitecture(sessionId);
      onPlanUpdated(p);
    } catch (e) {
      setRemediateError(
        e instanceof Error ? e.message : "Could not approve architecture",
      );
    } finally {
      setApproving(false);
    }
  };

  return (
    <div className="arch-validation">
      <div className={`arch-validation__banner arch-validation__banner--${v.overall}`}>
        <span className="arch-validation__overall">
          {plan.architecture_approved
            ? "Approved"
            : v.overall === "pass"
              ? "Looks consistent"
              : v.overall === "warn"
                ? "Needs review"
                : "Issues found"}
        </span>
        <span className="arch-validation__counts">
          {v.pass_count} pass · {v.warn_count} warn · {v.fail_count} fail
        </span>
      </div>

      {v.approval_hint ? (
        <p className="arch-validation__approval-hint">{v.approval_hint}</p>
      ) : null}

      <div className="arch-validation__toolbar">
        <span className="arch-validation__progress">
          {actionable.length === 0
            ? "No open issues"
            : `${v.unresolved_actionable_count ?? actionable.length} open · ${resolvedCount} reviewed`}
        </span>
        <div className="arch-validation__filters">
          {(["all", "fail", "warn"] as const).map((f) => (
            <button
              key={f}
              type="button"
              className={`arch-validation__filter ${filter === f ? "arch-validation__filter--active" : ""}`}
              onClick={() => setFilter(f)}
            >
              {f === "all" ? "All" : f === "fail" ? "Fails" : "Warnings"}
            </button>
          ))}
        </div>
      </div>

      <p className="arch-validation__intro">
        Click a chip to apply a fix. Fails with{" "}
        <strong>approval blocked</strong> need a structural fix, not only
        acknowledge.
      </p>

      {remediateError ? (
        <p className="chat-error arch-validation__error">{remediateError}</p>
      ) : null}

      <div className="arch-validation__approve-row">
        <button
          type="button"
          className="btn btn--primary"
          disabled={!v.can_approve || plan.architecture_approved || approving}
          onClick={handleApprove}
        >
          {plan.architecture_approved
            ? "Architecture approved"
            : approving
              ? "Approving…"
              : "Approve architecture"}
        </button>
        {onRegenerate ? (
          <button
            type="button"
            className="btn btn--ghost"
            onClick={onRegenerate}
          >
            Regenerate
          </button>
        ) : null}
      </div>

      {filtered.length === 0 ? (
        <p className="arch-validation__all-clear">
          No open {filter === "all" ? "" : filter} issues in this filter.
        </p>
      ) : null}

      {graphIssues.length > 0 ? (
        <section className="arch-inspector__section">
          <h3>Architecture-wide</h3>
          <ul className="arch-validation__list">
            {graphIssues.map((item) => (
              <FindingCard
                key={item.finding_id ?? item.code + item.message}
                item={item}
                sessionId={sessionId}
                onSelectNode={onSelectNode}
                onPlanUpdated={onPlanUpdated}
                applyingKey={applyingKey}
                setApplyingKey={setApplyingKey}
                setRemediateError={setRemediateError}
              />
            ))}
          </ul>
        </section>
      ) : null}

      {byNode.size > 0 ? (
        <section className="arch-inspector__section arch-inspector__section--flow">
          <h3>Per step</h3>
          <ul className="arch-flow-list">
            {plan.graph.nodes.map((node) => {
              const nodeIssues = byNode.get(node.id);
              if (!nodeIssues?.length) return null;
              const status = v.node_status[node.id] ?? "pass";
              return (
                <li key={node.id} className="arch-validation__step-block">
                  <button
                    type="button"
                    className={`arch-flow-list__btn arch-flow-list__btn--${status}`}
                    onClick={() => onSelectNode(node.id)}
                  >
                    <span
                      className={`arch-validation__dot arch-validation__dot--${status}`}
                    />
                    <span className="arch-flow-list__label">{node.label}</span>
                  </button>
                  <ul className="arch-validation__list arch-validation__list--nested">
                    {nodeIssues.map((item) => (
                      <FindingCard
                        key={item.finding_id ?? item.code}
                        item={item}
                        sessionId={sessionId}
                        onSelectNode={onSelectNode}
                        onPlanUpdated={onPlanUpdated}
                        applyingKey={applyingKey}
                        setApplyingKey={setApplyingKey}
                        setRemediateError={setRemediateError}
                      />
                    ))}
                  </ul>
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
