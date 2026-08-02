/* Severity-tagged assumption list — the "never silent" policy: every
   estimated quantity carries a visible assumption the contractor must
   verify. Extracted from Boq.jsx's inline rendering so Extraction/Compare
   pages can reuse it once they show gaps too. */
export default function GapReport({ gaps }) {
  if (!gaps?.length) return null;
  return (
    <>
      <h3 style={{ fontSize: 16, marginBottom: 10 }}>Gap report — {gaps.length} assumption(s) to verify</h3>
      <div className="glass-card" style={{ padding: 'var(--space-md)', marginBottom: 'var(--space-lg)' }}>
        <ul style={{ fontSize: 13, color: 'var(--ink-2)', margin: 0, paddingLeft: 18 }}>
          {gaps.map((g, i) => (
            <li key={i} style={{ marginBottom: i < gaps.length - 1 ? 8 : 0 }}>
              <strong style={{ color: 'var(--amber)' }}>[{g.severity}]</strong> {g.description} — {g.assumption} → {g.suggested_action}
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}
