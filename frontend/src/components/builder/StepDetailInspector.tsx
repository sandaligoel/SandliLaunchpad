import { ReuseBadge } from "@/architecture-flow/components/nodes/shared";
import type { ReuseDecision } from "@/architecture-flow/types/plan";
import { prettyJson, summarizeJsonEntries } from "@/components/builder/stepDetailIo";

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
};

function IoSection({
  kind,
  title,
  json,
}: {
  kind: "input" | "output";
  title: string;
  json: Record<string, unknown> | null | undefined;
}) {
  const entries = summarizeJsonEntries(
    json ?? undefined,
    kind === "input"
      ? "No input fields for this step."
      : "No output fields for this step.",
  );

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
      <label className="builder-io-block-label">
        Full {kind} JSON
      </label>
      <pre
        className="builder-io-pre"
        role="region"
        aria-label={`Step ${kind} JSON`}
      >
        {prettyJson(json)}
      </pre>
    </div>
  );
}

export function StepDetailInspector({ detail }: { detail: StepDetailPayload | null }) {
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
  const confidenceText =
    detail.confidence != null
      ? `${Math.round(detail.confidence <= 1 ? detail.confidence * 100 : detail.confidence)}%`
      : reuse === "build"
        ? "N/A (build new)"
        : "—";

  return (
    <div className="builder-step-sidebar">
      <div className="builder-col-head">
        <div className="builder-col-kicker">Inspector</div>
        <h3>Step Details</h3>
      </div>
      <div className="builder-step-body">
        <div className="builder-step-header">
          <div className="flex items-start justify-between gap-2">
            <h4 className="builder-step-title">{detail.label}</h4>
            <ReuseBadge reuse={reuse} />
          </div>
          {detail.description ? (
            <p className="builder-step-desc">{detail.description}</p>
          ) : null}
        </div>

        <dl className="builder-step-stats">
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
            <p className="builder-io-block-label">Tools used</p>
            <div className="builder-tools-list">
              {detail.tools.map((t) => (
                <span key={t}>{t}</span>
              ))}
            </div>
          </div>
        ) : null}

        <IoSection
          kind="input"
          title="Input information"
          json={detail.inputJson ?? null}
        />
        <IoSection
          kind="output"
          title="Output information"
          json={detail.outputJson ?? null}
        />
      </div>
    </div>
  );
}
