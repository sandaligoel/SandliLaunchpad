import { useCallback, useEffect, useState } from "react";
import { ReuseBadge } from "@/architecture-flow/components/nodes/shared";
import type { ReuseDecision } from "@/architecture-flow/types/plan";
import {
  resolveStepComponentKind,
  stepComponentKindHint,
  stepComponentKindLabel,
  type StepComponentKind,
} from "@/utils/stepComponentKind";
import {
  parseJsonObject,
  prettyJson,
  summarizeJsonEntries,
} from "@/components/builder/stepDetailIo";

export type StepDetailPayload = {
  id: string;
  label: string;
  description: string;
  reuse: string;
  confidence: number | null;
  catalogRationale?: string;
  lane?: string;
  status?: string;
  latencyMs?: number;
  inputJson?: Record<string, unknown> | null;
  outputJson?: Record<string, unknown> | null;
  tools?: string[];
  componentKind?: StepComponentKind;
  catalogAgentName?: string;
};

function ComponentKindBadge({ kind }: { kind: StepComponentKind }) {
  const cls =
    kind === "agent"
      ? "builder-kind-badge builder-kind-badge--agent"
      : kind === "tool"
        ? "builder-kind-badge builder-kind-badge--tool"
        : "builder-kind-badge builder-kind-badge--function";
  return (
    <span className={cls} title={stepComponentKindHint(kind)}>
      {stepComponentKindLabel(kind)}
    </span>
  );
}

type IoJsonKind = "input" | "output";

function IoSection({
  kind,
  title,
  json,
  disabled,
  onSave,
}: {
  kind: IoJsonKind;
  title: string;
  json: Record<string, unknown> | null | undefined;
  disabled?: boolean;
  onSave?: (kind: IoJsonKind, value: Record<string, unknown>) => void;
}) {
  const [draft, setDraft] = useState(() => prettyJson(json));
  const [error, setError] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    setDraft(prettyJson(json));
    setError(null);
    setDirty(false);
  }, [json, kind]);

  const entries = summarizeJsonEntries(
    json ?? undefined,
    kind === "input"
      ? "No input fields for this step."
      : "No output fields for this step.",
  );

  const commit = useCallback(() => {
    if (disabled || !onSave) return;
    const result = parseJsonObject(draft);
    if (!result.ok) {
      setError(result.error);
      return;
    }
    setError(null);
    setDirty(false);
    onSave(kind, result.value);
  }, [disabled, draft, kind, onSave]);

  return (
    <div className={`builder-io-section builder-io-section--${kind}`}>
      <h4>{title}</h4>
      <ul className="builder-io-keys">
        {entries.map((row) =>
          row.key ? (
            <li key={row.key}>
              <code>{row.key}</code>
              {" — "}
              {row.preview}
            </li>
          ) : (
            <li key="empty">{row.preview}</li>
          ),
        )}
      </ul>
      <label className="builder-io-block-label" htmlFor={`builder-io-${kind}`}>
        Full {kind} JSON
      </label>
      <textarea
        id={`builder-io-${kind}`}
        className="builder-io-textarea"
        rows={10}
        spellCheck={false}
        disabled={disabled || !onSave}
        value={draft}
        onChange={(e) => {
          setDraft(e.target.value);
          setDirty(true);
          if (error) setError(null);
        }}
        onBlur={() => {
          if (dirty) commit();
        }}
        aria-label={`Step ${kind} JSON`}
        aria-invalid={error ? true : undefined}
      />
      {error ? <p className="builder-io-error">{error}</p> : null}
      {onSave && !disabled ? (
        <div className="builder-io-actions">
          <button
            type="button"
            className="builder-io-apply"
            onClick={commit}
            disabled={!dirty}
          >
            Apply JSON
          </button>
          {dirty ? (
            <span className="builder-io-hint">Unsaved edits</span>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export function StepDetailInspector({
  detail,
  disabled,
  onIoJsonChange,
}: {
  detail: StepDetailPayload | null;
  disabled?: boolean;
  onIoJsonChange?: (
    nodeId: string,
    patch: {
      input_json?: Record<string, unknown>;
      output_json?: Record<string, unknown>;
    },
  ) => void;
}) {
  const handleSave = useCallback(
    (kind: IoJsonKind, value: Record<string, unknown>) => {
      if (!detail?.id || !onIoJsonChange) return;
      onIoJsonChange(
        detail.id,
        kind === "input" ? { input_json: value } : { output_json: value },
      );
    },
    [detail?.id, onIoJsonChange],
  );

  if (!detail) {
    return (
      <div className="builder-step-sidebar">
        <div className="builder-col-head">
          <div className="builder-col-kicker">Inspector</div>
          <h3>Step Details</h3>
          <p>Select a step on the canvas or from the agent list.</p>
        </div>
        <div className="builder-step-body">
          <p className="builder-step-empty">
            Click a workflow step to view input/output information.
          </p>
        </div>
      </div>
    );
  }

  const reuse = (detail.reuse || "build") as ReuseDecision;
  const componentKind =
    detail.componentKind ?? resolveStepComponentKind(undefined, reuse);
  const confidenceText =
    detail.confidence != null
      ? `${Math.round(detail.confidence <= 1 ? detail.confidence * 100 : detail.confidence)}%`
      : reuse === "build"
        ? "N/A (build new)"
        : "—";

  const sidebarKindClass = `builder-step-sidebar--${componentKind}`;

  return (
    <div className={`builder-step-sidebar ${sidebarKindClass}`}>
      <div className={`builder-step-kind-banner builder-step-kind-banner--${componentKind}`}>
        <span className="builder-step-kind-banner__label">
          {stepComponentKindLabel(componentKind)}
        </span>
        <span className="builder-step-kind-banner__hint">
          {stepComponentKindHint(componentKind)}
        </span>
      </div>
      <div className="builder-col-head">
        <div className="builder-col-kicker">Inspector</div>
        <h3>Step Details</h3>
      </div>
      <div className="builder-step-body">
        <div className="builder-step-header">
          <div className="flex items-start justify-between gap-2">
            <h4 className="builder-step-title">{detail.label}</h4>
            <div className="flex flex-shrink-0 flex-wrap items-center justify-end gap-1">
              <ComponentKindBadge kind={componentKind} />
              <ReuseBadge reuse={reuse} />
            </div>
          </div>
          {detail.catalogAgentName && componentKind === "agent" ? (
            <p className="builder-step-catalog-ref">
              Catalog: <strong>{detail.catalogAgentName}</strong>
            </p>
          ) : null}
          {detail.description ? (
            <p className="builder-step-desc">{detail.description}</p>
          ) : null}
        </div>

        <dl className="builder-step-stats">
          <div>
            <dt>Component</dt>
            <dd>
              <ComponentKindBadge kind={componentKind} />
            </dd>
          </div>
          <div>
            <dt>Lane</dt>
            <dd className="capitalize">{detail.lane || "execution"}</dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd className="capitalize">{detail.status || "idle"}</dd>
          </div>
          <div>
            <dt>Latency</dt>
            <dd>{detail.latencyMs != null ? `${detail.latencyMs}ms` : "—"}</dd>
          </div>
          <div>
            <dt>Match</dt>
            <dd>{confidenceText}</dd>
          </div>
        </dl>

        {detail.tools && detail.tools.length > 0 ? (
          <div>
            <p className="builder-io-block-label">
              Supporting tools{" "}
              <span className="builder-io-block-sublabel">(integrations)</span>
            </p>
            <div className="builder-tools-list">
              {detail.tools.map((t) => (
                <span key={t} className="builder-tool-chip" title="Integration tool">
                  <span className="builder-tool-chip-kind">Tool</span>
                  {t}
                </span>
              ))}
            </div>
          </div>
        ) : null}

        <IoSection
          kind="input"
          title="Input information"
          json={detail.inputJson ?? null}
          disabled={disabled}
          onSave={onIoJsonChange ? handleSave : undefined}
        />
        <IoSection
          kind="output"
          title="Output information"
          json={detail.outputJson ?? null}
          disabled={disabled}
          onSave={onIoJsonChange ? handleSave : undefined}
        />
      </div>
    </div>
  );
}
