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
          title={
            spec.status === "ready"
              ? "Ready for Phase 3"
              : spec.status === "sufficient"
                ? "Core spec complete — optional fields remain"
                : "Gathering requirements & flow"
          }
        >
          {spec.status === "ready"
            ? "Ready"
            : spec.status === "sufficient"
              ? "Sufficient"
              : "In progress"}
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

      {spec.catalog_hints && spec.catalog_hints.length > 0 ? (
        <section className="spec-catalog">
          <h3>Similar Affine agents</h3>
          <ul className="spec-catalog__list">
            {spec.catalog_hints.map((h) => (
              <li key={h.agent_id}>
                <strong>{h.name}</strong>
                <span className="spec-catalog__meta">
                  {h.category}
                  {h.origin_client ? ` · ${h.origin_client}` : ""}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

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

      {spec.graph_draft && spec.graph_draft.nodes.length > 0 ? (
        <section className="spec-graph">
          <h3>Graph draft (Phase 3)</h3>
          <p className="spec-graph__meta">
            {spec.graph_draft.nodes.length} nodes, {spec.graph_draft.edges.length}{" "}
            edges
          </p>
          <ul className="spec-graph__nodes">
            {spec.graph_draft.nodes.map((n) => (
              <li key={n.id}>
                <code>{n.id}</code> — {n.label}
                {n.type === "agent" && n.agent_id ? (
                  <span className="spec-graph__agent"> ({n.agent_id})</span>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {spec.architecture_blueprint ? (
        <section className="spec-blueprint">
          <h3>Architecture blueprint</h3>
          <pre className="spec-blueprint__body">{spec.architecture_blueprint}</pre>
        </section>
      ) : null}
    </aside>
  );
}
