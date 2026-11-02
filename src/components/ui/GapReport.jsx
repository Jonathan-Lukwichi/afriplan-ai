import { SEVERITY, toCheck } from '../../lib/plainWords';

/* "Things to check" — the never-silent list: what a person must decide, most urgent first, each
   with what was assumed and what to do. Notes that ask for no decision stay available, folded away. */
const ORDER = { critical: 0, high: 1, medium: 2, low: 3 };
const COLOR = { critical: 'var(--rose)', high: 'var(--rose)', medium: 'var(--amber)', low: 'var(--ink-muted)' };

function GapList({ gaps }) {
  return (
    <ul style={{ fontSize: 13, color: 'var(--ink-2)', margin: 0, paddingLeft: 18 }}>
      {gaps.map((g, i) => (
        <li key={i} style={{ marginBottom: i < gaps.length - 1 ? 10 : 0 }}>
          <strong style={{ color: COLOR[g.severity] || 'var(--ink)' }} title={SEVERITY[g.severity]?.meaning}>
            {SEVERITY[g.severity]?.label || g.severity}:
          </strong>{' '}
          {g.description}
          {g.assumption && <span style={{ display: 'block', color: 'var(--ink-muted)' }}>What the app did: {g.assumption}</span>}
          {g.suggested_action && <span style={{ display: 'block' }}>What to do: {g.suggested_action}</span>}
        </li>
      ))}
    </ul>
  );
}

export default function GapReport({ gaps }) {
  if (!gaps?.length) return null;
  const sorted = [...gaps].sort((a, b) => (ORDER[a.severity] ?? 9) - (ORDER[b.severity] ?? 9));
  const decide = toCheck(sorted);
  const notes = sorted.filter((g) => !decide.includes(g));
  return (
    <>
      <h3 style={{ fontSize: 16, marginBottom: 4 }}>Things to check — {decide.length}</h3>
      <p style={{ fontSize: 13, color: 'var(--ink-muted)', margin: '0 0 10px' }}>
        {decide.length
          ? 'What the app could not confirm from the drawings. Go through the “Must check” ones before sending the quote.'
          : 'Nothing needs a decision. The notes below show how the app worked some lines out.'}
      </p>
      {decide.length > 0 && (
        <div className="glass-card" style={{ padding: 'var(--space-md)', marginBottom: 'var(--space-md)' }} data-testid="gaps-to-check">
          <GapList gaps={decide} />
        </div>
      )}
      {notes.length > 0 && (
        <details className="glass-card" style={{ padding: 'var(--space-md)', marginBottom: 'var(--space-lg)' }} data-testid="gaps-notes">
          <summary style={{ cursor: 'pointer', fontSize: 14 }}>For information — {notes.length}</summary>
          <div style={{ marginTop: 10 }}><GapList gaps={notes} /></div>
        </details>
      )}
    </>
  );
}
