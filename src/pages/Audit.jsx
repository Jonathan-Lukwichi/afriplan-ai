import { useState } from 'react';
import { api } from '../api/client';
import PageHeader from '../components/ui/PageHeader';
import MetricTile from '../components/ui/MetricTile';
import FindingsTable from '../components/ui/FindingsTable';

const zar = (v) => `R ${Number(v || 0).toLocaleString('en-ZA', { maximumFractionDigits: 0 })}`;

/* Audit a BOQ — upload any priced BOQ workbook (a consultant's, a tender you
   are checking, your own) and get every defect ranked by rand value at risk.
   Backed by POST /api/audit/boq (api/audit: arithmetic, priced lines left out
   of totals, unpriced lines, duplicates, roll-ups, contingency, sheets missing
   from the summary, feeders without earth/terminations). Needs no drawings. */
export default function Audit() {
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const run = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api.audit.boq(file));
    } catch (e) {
      setError(e.detail?.detail || e.message || 'Could not audit this workbook');
    } finally {
      setBusy(false);
    }
  };

  const s = result?.summary;

  return (
    <div style={{ maxWidth: 1440, padding: 'var(--space-xl) var(--space-md)' }}>
      <PageHeader
        title="Audit a Bill of Quantities"
        subtitle="Upload a priced BOQ workbook. Every line is checked — arithmetic, priced lines missing from totals, unpriced items, duplicates, section roll-ups, contingency, sheets missing from the summary, feeders without earth or terminations — and ranked by the money at risk."
      />

      <div className="glass-card" style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap', padding: 'var(--space-md)', marginBottom: 'var(--space-lg)' }}>
        <input type="file" accept=".xlsx" data-testid="audit-file"
               style={{ minHeight: 44, padding: '8px 0', maxWidth: '100%', fontSize: 14 }}
               onChange={(e) => { setFile(e.target.files?.[0] || null); setResult(null); setError(null); }} />
        <button onClick={run} disabled={!file || busy} className="btn-gradient" style={{ padding: '10px 22px', fontSize: 14 }}>
          {busy ? 'Auditing…' : 'Audit this BoQ'}
        </button>
        <span style={{ fontSize: 13, color: 'var(--ink-muted)' }}>
          SA bill layout: a Summary sheet plus one sheet per building (ITEM NO · DESCRIPTION · UOM · QTY · RATE · SUB TOTAL).
        </span>
      </div>

      {error && <p style={{ color: 'var(--rose)' }}>{error}</p>}

      {result && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 'var(--space-md)', marginBottom: 'var(--space-lg)' }}>
            <MetricTile label="Bills found" value={result.bills.length} />
            <MetricTile label="Priced lines" value={result.bills.reduce((n, b) => n + b.lines, 0).toLocaleString('en-ZA')} />
            <MetricTile label="Findings" value={`${s.count} (${s.high} high)`} />
            <MetricTile label="Value at risk" value={zar(s.value_at_risk_zar)} />
          </div>

          {s.by_rule.length > 0 && (
            <>
              <h3 style={{ fontSize: 16, marginBottom: 10 }}>By rule</h3>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 'var(--space-lg)' }}>
                {s.by_rule.map((r) => (
                  <span key={r.rule} className="glass-card" style={{ padding: '6px 12px', fontSize: 13 }}>
                    <strong>{r.rule}</strong> × {r.count} · {zar(r.value_at_risk_zar)}
                  </span>
                ))}
              </div>
            </>
          )}

          <h3 style={{ fontSize: 16, marginBottom: 10 }}>Findings</h3>
          <FindingsTable findings={result.findings} showBuilding />

          <h3 style={{ fontSize: 16, margin: 'var(--space-lg) 0 10px' }}>Bills read from the workbook</h3>
          <div className="glass-card" style={{ overflowX: 'auto', padding: 4 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: 'var(--paper-2)', textAlign: 'left' }}>
                  {['Bill', 'In summary', 'Lines', 'Stated total', 'Sum of lines', 'Error cells'].map((h) => (
                    <th key={h} style={{ padding: '8px 10px', borderBottom: '1px solid var(--hairline-2)' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.bills.map((b) => (
                  <tr key={b.name} style={{ borderBottom: '1px solid var(--hairline)' }}>
                    <td style={{ padding: '8px 10px' }}>{b.name}</td>
                    <td style={{ padding: '8px 10px' }}>{b.in_summary ? 'yes' : <strong style={{ color: 'var(--rose)' }}>no</strong>}</td>
                    <td style={{ padding: '8px 10px' }}>{b.lines}</td>
                    <td style={{ padding: '8px 10px' }}>{zar(b.stated_total_zar)}</td>
                    <td style={{ padding: '8px 10px' }}>{zar(b.sum_of_lines_zar)}</td>
                    <td style={{ padding: '8px 10px' }}>{b.errors}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
