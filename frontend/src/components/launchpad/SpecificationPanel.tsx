import type { ArchitectureSpec } from "@/api/affine/types";
import {
  USER_INTERVIEW_ARCHITECTURE_KEYS,
  USER_INTERVIEW_FIELD_KEYS,
} from "@/api/affine/types";

interface Props {
  spec: ArchitectureSpec;
}

export function SpecificationPanel({ spec }: Props) {
  const keys = [...USER_INTERVIEW_ARCHITECTURE_KEYS];
  const known = keys.filter(
    (k) => spec.fields[k]?.status === "known" && spec.fields[k]?.value,
  ).length;
  const total = keys.length;
  const pct = total ? Math.round((known / total) * 100) : 0;

  return (
    <aside className="spec-panel">
      <header className="spec-panel__header">
        <h2>Specification</h2>
        <span className={`spec-badge spec-badge--${spec.status}`}>
          {spec.status === "ready" ? "Ready" : "In progress"}
        </span>
      </header>

      <div className="spec-progress">
        <div className="spec-progress__bar">
          <div className="spec-progress__fill" style={{ width: `${pct}%` }} />
        </div>
        <p className="spec-progress__label">
          {known} of {total} fields ({pct}%) · {known}/
          {USER_INTERVIEW_FIELD_KEYS.length} chat topics
        </p>
      </div>

      <dl className="spec-fields">
        {keys.map((key) => {
          const field = spec.fields[key];
          const knownField = field?.status === "known" && field.value;
          return (
            <div key={key} className="spec-field">
              <dt>{field?.label ?? key}</dt>
              <dd
                className={
                  knownField
                    ? "spec-field__value spec-field__value--known"
                    : "spec-field__value spec-field__value--pending"
                }
              >
                {knownField ? field.value : "Pending…"}
              </dd>
            </div>
          );
        })}
      </dl>

      {spec.architecture_blueprint ? (
        <section className="spec-blueprint">
          <h3>Architecture blueprint</h3>
          <pre className="spec-blueprint__body">{spec.architecture_blueprint}</pre>
        </section>
      ) : null}
    </aside>
  );
}
