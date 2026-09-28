import ConfidenceBadge from './ConfidenceBadge';
import { UNITS } from '../../lib/plainWords';

/* The priced bill, one row per line. Shared by every BOQ-consuming page. Column names
   and units are plain words (hover a unit for its meaning); every number uses the same
   South African format. */
const num = (v, digits = 2) => Number(v || 0).toLocaleString('en-ZA', { minimumFractionDigits: 0, maximumFractionDigits: digits });

export default function LineItemsTable({ items }) {
  return (
    <div className="glass-card" style={{ overflowX: 'auto', padding: 4 }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ background: 'var(--paper-2)', textAlign: 'left' }}>
            {['#', 'Section', 'What', 'Unit', 'How many', 'Price each (R)', 'Line total (R)', 'Where it comes from'].map((h) => (
              <th key={h} style={{ padding: '8px 10px', borderBottom: '1px solid var(--hairline-2)' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((it, i) => (
            <tr key={i} style={{ borderBottom: '1px solid var(--hairline)' }}>
              <td style={{ padding: '8px 10px' }}>{it.item_no}</td>
              <td style={{ padding: '8px 10px' }}>{it.section}</td>
              <td style={{ padding: '8px 10px' }} title={it.assumption || it.notes || undefined}>{it.description}</td>
              <td style={{ padding: '8px 10px', whiteSpace: 'nowrap' }} title={UNITS[it.unit]?.meaning}>{UNITS[it.unit]?.label || it.unit}</td>
              <td style={{ padding: '8px 10px', textAlign: 'right' }}>{num(it.qty)}</td>
              <td style={{ padding: '8px 10px', textAlign: 'right' }}>{num(it.unit_price_zar)}</td>
              <td style={{ padding: '8px 10px', textAlign: 'right' }}>{num(it.total_zar)}</td>
              <td style={{ padding: '8px 10px' }}><ConfidenceBadge source={it.source} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
