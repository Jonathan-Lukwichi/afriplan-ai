import ConfidenceBadge from './ConfidenceBadge';

/* Extracted from Boq.jsx so any future BOQ-consuming page (Compare's
   per-run drill-down, a future revision-history view) shares one table,
   not a copy-pasted one. Now also surfaces ConfidenceBadge per item — the
   original app defined the 6-way ItemConfidence scheme but never rendered
   it anywhere. */
export default function LineItemsTable({ items }) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ background: 'var(--paper-2)', textAlign: 'left' }}>
            {['#', 'Section', 'Description', 'Unit', 'Qty', 'Rate (R)', 'Total (R)', 'Source'].map((h) => (
              <th key={h} style={{ padding: '8px 10px', borderBottom: '1px solid var(--hairline-2)' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((it, i) => (
            <tr key={i} style={{ borderBottom: '1px solid var(--hairline)' }}>
              <td style={{ padding: '8px 10px' }}>{it.item_no}</td>
              <td style={{ padding: '8px 10px' }}>{it.section}</td>
              <td style={{ padding: '8px 10px' }}>{it.description}</td>
              <td style={{ padding: '8px 10px' }}>{it.unit}</td>
              <td style={{ padding: '8px 10px' }}>{it.qty}</td>
              <td style={{ padding: '8px 10px' }}>{it.unit_price_zar.toLocaleString('en-ZA')}</td>
              <td style={{ padding: '8px 10px' }}>{it.total_zar.toLocaleString('en-ZA')}</td>
              <td style={{ padding: '8px 10px' }}><ConfidenceBadge source={it.source} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
