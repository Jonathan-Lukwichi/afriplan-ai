/* Shows the drawing's own symbol dictionary (agent/shared/legend.py) —
   read but never displayed in the original app's UI. Surfaced here on the
   Extraction page once a run passes, since it's the direct evidence behind
   the gap report (a legend entry with no matching billed line item is
   exactly what GapReport flags). */
export default function LegendPanel({ legend }) {
  if (!legend?.entries?.length) return null;
  return (
    <div style={{ marginTop: 'var(--space-lg)' }}>
      <h3 style={{ fontSize: 16, marginBottom: 10 }}>
        Legend ({legend.entries.length} symbol{legend.entries.length === 1 ? '' : 's'} — {legend.source.toUpperCase()})
      </h3>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: 'var(--paper-2)', textAlign: 'left' }}>
              {['Symbol', 'Description', 'Canonical item', 'Section', 'Qty'].map((h) => (
                <th key={h} style={{ padding: '8px 10px', borderBottom: '1px solid var(--hairline-2)' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {legend.entries.map((e, i) => (
              <tr key={i} style={{ borderBottom: '1px solid var(--hairline)' }}>
                <td style={{ padding: '8px 10px', fontFamily: 'var(--mono)' }}>{e.symbol_key}</td>
                <td style={{ padding: '8px 10px' }}>{e.description}</td>
                <td style={{ padding: '8px 10px' }}>{e.canonical_item}</td>
                <td style={{ padding: '8px 10px' }}>{e.section}</td>
                <td style={{ padding: '8px 10px' }}>{e.qty_in_legend ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
