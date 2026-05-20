import type { ArchitectureSpec } from "../types";
import { FIELD_GROUPS, FIELD_ORDER } from "../types";

interface Props {
  spec: ArchitectureSpec;
}

export function SpecificationPanel({ spec }: Props) {
  const known = FIELD_ORDER.filter((k) => spec.fields[k]?.status === "known").length;
  const total = FIELD_ORDER.length;
  const pct = Math.round((known / total) * 100);

  return (
    <aside className="spec-panel">
      <header className="spec-panel__header">
        <h2>Specification</h2>
        <span
          className={`spec-badge spec-badge--${spec.status}`}
          title={spec.status === "ready" ? "Ready for Phase 3" : "Gathering requirements & flow"}
        >
          {spec.status === "ready" ? "Ready" : "In progress"}
        </span>
      </header>

      <div className="spec-progress">
        <div className="spec-progress__bar">
          <div className="spec-progress__fill" style={{ width: `${pct}%` }} />
        </div>
        <p className="spec-progress__label">
          {known} of {total} fields confirmed ({pct}%)
        </p>
      </div>

      <ul className="spec-checklist">
        {FIELD_ORDER.map((key) => {
          const field = spec.fields[key];
          const done = field?.status === "known" && field.value;
          return (
            <li
              key={key}
              className={`spec-checklist__item ${done ? "spec-checklist__item--done" : ""}`}
            >
              <span className="spec-checklist__mark" aria-hidden>
                {done ? "✓" : "○"}
              </span>
              <span className="spec-checklist__label">{field?.label ?? key}</span>
            </li>
          );
        })}
      </ul>

      <dl className="spec-fields">
        {Object.entries(FIELD_GROUPS).map(([groupId, group]) => (
          <div key={groupId} className="spec-field-group">
            <h3 className="spec-field-group__title">{group.title}</h3>
            {group.keys.map((key) => {
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
          </div>
        ))}
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
