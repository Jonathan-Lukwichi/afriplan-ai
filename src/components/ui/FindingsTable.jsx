/* BOQ audit findings (api/audit): one row per rule violation, ranked by
   severity then rand value at risk. Shared by the BOQ page's Audit tab and
   the Audit-a-BOQ page. */
const SEV_COLOR = { critical: 'var(--rose)', high: 'var(--rose)', medium: 'var(--amber)', low: 'var(--ink-muted)' };

const zar = (v) => `R ${Number(v || 0).toLocaleString('en-ZA', { maximumFractionDigits: 0 })}`;

export default function FindingsTable({ findings, showBuilding = false }) {
  if (!findings?.length) {
    return (
      <p style={{ fontSize: 14, color: 'var(--emerald)' }}>
        No arithmetic, pricing, duplicate or missing-companion problems found.
      </p>
    );
  }
  const headers = ['Severity', 'Rule', ...(showBuilding ? ['Bill'] : []), 'Location', 'Finding', 'Value at risk', 'Action'];
  return (
    <div className="glass-card" style={{ overflowX: 'auto', padding: 4 }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }} data-testid="findings-table">
        <thead>
          <tr style={{ background: 'var(--paper-2)', textAlign: 'left' }}>
            {headers.map((h) => (
              <th key={h} style={{ padding: '8px 10px', borderBottom: '1px solid var(--hairline-2)' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {findings.map((f, i) => (
            <tr key={i} style={{ borderBottom: '1px solid var(--hairline)' }}>
              <td style={{ padding: '8px 10px', color: SEV_COLOR[f.severity] || 'var(--ink)', fontWeight: 600 }}>{f.severity}</td>
              <td style={{ padding: '8px 10px' }}>{f.rule}</td>
              {showBuilding && <td style={{ padding: '8px 10px' }}>{f.building}</td>}
              <td style={{ padding: '8px 10px' }}>{f.location}</td>
              <td style={{ padding: '8px 10px' }}>{f.message}</td>
              <td style={{ padding: '8px 10px', whiteSpace: 'nowrap' }}>{zar(f.value_at_risk_zar)}</td>
              <td style={{ padding: '8px 10px', color: 'var(--ink-2)' }}>{f.suggested_action}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
