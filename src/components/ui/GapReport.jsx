import { SEVERITY } from '../../lib/plainWords';

/* "Things to check" — the never-silent list: everything the app had to guess or could not
   confirm, most urgent first, each with what was assumed and what to do. */
const ORDER = { critical: 0, high: 1, medium: 2, low: 3 };
const COLOR = { critical: 'var(--rose)', high: 'var(--rose)', medium: 'var(--amber)', low: 'var(--ink-muted)' };

export default function GapReport({ gaps }) {
  if (!gaps?.length) return null;
  const sorted = [...gaps].sort((a, b) => (ORDER[a.severity] ?? 9) - (ORDER[b.severity] ?? 9));
  return (
    <>
      <h3 style={{ fontSize: 16, marginBottom: 4 }}>Things to check — {gaps.length}</h3>
      <p style={{ fontSize: 13, color: 'var(--ink-muted)', margin: '0 0 10px' }}>
        Everything the app had to guess or could not confirm. Go through the “Must check” ones before sending the quote.
      </p>
      <div className="glass-card" style={{ padding: 'var(--space-md)', marginBottom: 'var(--space-lg)' }}>
        <ul style={{ fontSize: 13, color: 'var(--ink-2)', margin: 0, paddingLeft: 18 }}>
          {sorted.map((g, i) => (
            <li key={i} style={{ marginBottom: i < sorted.length - 1 ? 10 : 0 }}>
              <strong style={{ color: COLOR[g.severity] || 'var(--ink)' }} title={SEVERITY[g.severity]?.meaning}>
                {SEVERITY[g.severity]?.label || g.severity}:
              </strong>{' '}
              {g.description}
              {g.assumption && <span style={{ display: 'block', color: 'var(--ink-muted)' }}>What the app did: {g.assumption}</span>}
              {g.suggested_action && <span style={{ display: 'block' }}>What to do: {g.suggested_action}</span>}
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}
