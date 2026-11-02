import { useEffect, useState } from 'react';
import { api } from '../../api/client';

/* Extraction accuracy (GET /api/audit/reading/{run}) — how much of what is drawn the app read,
   judged against a real priced bill. Prices play no part. Accuracy needs that truth, so the panel
   only appears for a reference project on this machine; for any other upload there is nothing to
   compare with and it stays hidden. */
const pct = (v) => `${(v * 100).toFixed(1)} %`;

export default function ExtractionAccuracyPanel({ runId }) {
  const [reading, setReading] = useState(null);

  useEffect(() => {
    if (!runId) return;
    setReading(null);
    api.audit.reading(runId).then(setReading).catch(() => setReading(null));
  }, [runId]);

  if (!reading?.available) return null;
  const facts = [
    ['Items found', `${reading.items_found} of ${reading.items_judged}`],
    ['Share of value found', pct(reading.coverage)],
    ['Quantity accuracy', pct(reading.qty_accuracy)],
    ['Within 10 % of the real quantity', reading.items_within_10pct],
  ];

  return (
    <div className="glass-card" style={{ padding: 'var(--space-md)', marginTop: 'var(--space-lg)' }} data-testid="extraction-accuracy-panel">
      <h3 style={{ fontSize: 16, margin: '0 0 4px' }}>Extraction accuracy</h3>
      <p style={{ fontSize: 34, fontWeight: 700, margin: '0 0 2px', lineHeight: 1.15 }} data-testid="extraction-accuracy">
        {pct(reading.reading_score)}
      </p>
      <p style={{ fontSize: 13, color: 'var(--ink-muted)', margin: '0 0 12px' }}>
        Only what is counted or measured on the drawings, compared with the real priced bill for {reading.project}. Prices are not part of this score.
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 12 }}>
        {facts.map(([label, value]) => (
          <div key={label}>
            <div style={{ fontSize: 18, fontWeight: 600 }}>{value}</div>
            <div style={{ fontSize: 13, color: 'var(--ink-muted)' }}>{label}</div>
          </div>
        ))}
      </div>
      {reading.biggest_misses?.length > 0 && (
        <>
          <h4 style={{ fontSize: 14, margin: '14px 0 6px' }}>Biggest differences from the bill</h4>
          <ul style={{ fontSize: 13, margin: 0, paddingLeft: 18 }}>
            {reading.biggest_misses.map((m) => (
              <li key={m.item} style={{ marginBottom: 4 }}>
                {m.item}: {m.verdict} <span style={{ color: 'var(--ink-muted)' }}>({(m.points_lost * 100).toFixed(1)} points)</span>
              </li>
            ))}
          </ul>
          <p style={{ fontSize: 13, color: 'var(--ink-muted)', margin: '8px 0 0' }}>
            A difference is not always a misread: the bill can differ from the drawing.
          </p>
        </>
      )}
    </div>
  );
}
