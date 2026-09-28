import { AUDIT_RULES, SEVERITY, SOURCE, TERMS, UNITS } from '../../lib/plainWords';

/* "What do these words mean?" — every label the app shows, in plain language.
   Collapsed by default; `show` picks the groups relevant to the page. */
const GROUPS = {
  source: ['Where each line comes from', Object.values(SOURCE).map((s) => [s.label, s.meaning])],
  severity: ['How urgent', Object.values(SEVERITY).map((s) => [s.label, s.meaning])],
  units: ['Units', [...new Map(Object.entries(UNITS).map(([k, u]) => [u.label, [`${k} (${u.label})`, u.meaning]])).values()]],
  terms: ['Words on the bill', TERMS],
  audit: ['Problems the audit looks for', Object.values(AUDIT_RULES).map((r) => [r.label, r.meaning])],
};

export default function Glossary({ show = ['source', 'severity', 'units', 'terms'] }) {
  return (
    <details className="glass-card" style={{ padding: 'var(--space-md)', marginBottom: 'var(--space-md)' }} data-testid="glossary">
      <summary style={{ cursor: 'pointer', fontWeight: 600, fontSize: 14, minHeight: 28 }}>
        What do these words mean?
      </summary>
      {show.map((key) => {
        const [title, rows] = GROUPS[key];
        return (
          <div key={key} style={{ marginTop: 14 }}>
            <h4 style={{ fontSize: 14, margin: '0 0 6px' }}>{title}</h4>
            <dl style={{ display: 'grid', gridTemplateColumns: 'minmax(120px, 220px) 1fr', gap: '6px 16px', margin: 0, fontSize: 13 }}>
              {rows.map(([term, meaning]) => [
                <dt key={`${term}-t`} style={{ fontWeight: 600 }}>{term}</dt>,
                <dd key={`${term}-d`} style={{ margin: 0, color: 'var(--ink-2)' }}>{meaning}</dd>,
              ])}
            </dl>
          </div>
        );
      })}
    </details>
  );
}
