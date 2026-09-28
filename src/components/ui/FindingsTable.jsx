import { AUDIT_RULES, SEVERITY } from '../../lib/plainWords';

/* BOQ audit findings (api/audit): one row per problem, most urgent first, then by money
   at risk. Rule codes are shown as plain names (hover for the full meaning). Shared by
   the BOQ page's Audit tab and the Audit-a-BOQ page. */
const SEV_COLOR = { critical: 'var(--rose)', high: 'var(--rose)', medium: 'var(--amber)', low: 'var(--ink-muted)' };

const zar = (v) => `R ${Number(v || 0).toLocaleString('en-ZA', { maximumFractionDigits: 0 })}`;

export default function FindingsTable({ findings, showBuilding = false }) {
  if (!findings?.length) {
    return (
      <p style={{ fontSize: 14, color: 'var(--emerald)' }}>
        No problems found: the sums add up, every line is priced and totalled, nothing is billed twice,
        and every cable has its earth wire, end connections and installation.
      </p>
    );
  }
  const headers = ['How urgent', 'Problem', ...(showBuilding ? ['Bill'] : []), 'Where', 'Details', 'Money at risk', 'What to do'];
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
              <td style={{ padding: '8px 10px', color: SEV_COLOR[f.severity] || 'var(--ink)', fontWeight: 600, whiteSpace: 'nowrap' }}
                  title={SEVERITY[f.severity]?.meaning}>
                {SEVERITY[f.severity]?.label || f.severity}
              </td>
              <td style={{ padding: '8px 10px' }} title={AUDIT_RULES[f.rule]?.meaning}>
                {AUDIT_RULES[f.rule]?.label || f.rule}
                <span style={{ display: 'block', fontSize: 11, color: 'var(--ink-muted)' }}>{f.rule}</span>
              </td>
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
