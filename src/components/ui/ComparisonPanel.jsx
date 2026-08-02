import MetricTile from './MetricTile';

/* Renders a PipelineComparison (agent/comparison/models.py). Replaces the
   original app's Streamlit render_comparison_panel() — same content, a
   React component instead, since this is now a real page, not a dead
   feature (see CLAUDE.md, decision #3). */
export default function ComparisonPanel({ cmp, onDownloadPdf }) {
  const sections = Object.values(cmp.section_agreements || {}).sort((a, b) => a.section.localeCompare(b.section));

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 'var(--space-md)', marginBottom: 'var(--space-lg)' }}>
        <MetricTile label="Total difference" value={cmp.total_difference_pct != null ? `${(cmp.total_difference_pct * 100).toFixed(1)}%` : '—'} />
        <MetricTile label="Agreement score" value={`${Math.round(cmp.agreement_score * 100)}%`} />
        <MetricTile
          label="Winner vs baseline"
          value={cmp.winner_vs_baseline && cmp.winner_vs_baseline !== 'no_baseline' ? cmp.winner_vs_baseline.toUpperCase() : '—'}
        />
        <MetricTile label="PDF cost" value={`R ${cmp.pdf_cost_zar.toFixed(2)}`} />
      </div>

      <p style={{ fontSize: 14, color: 'var(--ink-2)', marginBottom: 'var(--space-lg)' }}>
        <strong>PDF total ex VAT:</strong> R {cmp.pdf_total_excl_vat.toLocaleString('en-ZA', { maximumFractionDigits: 2 })}
        {'  |  '}
        <strong>DXF total ex VAT:</strong> R {cmp.dxf_total_excl_vat.toLocaleString('en-ZA', { maximumFractionDigits: 2 })}
      </p>

      <h3 style={{ fontSize: 16, marginBottom: 10 }}>Section-by-section breakdown</h3>
      <div className="glass-card" style={{ overflowX: 'auto', marginBottom: 'var(--space-lg)', padding: 4 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: 'var(--paper-2)', textAlign: 'left' }}>
              {['Section', 'PDF (R)', 'DXF (R)', 'Δ (R)', 'Δ %', 'Both', 'PDF only', 'DXF only'].map((h) => (
                <th key={h} style={{ padding: '8px 10px', borderBottom: '1px solid var(--hairline-2)' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sections.length === 0 && (
              <tr><td colSpan={8} style={{ padding: 10, color: 'var(--ink-muted)' }}>No overlapping sections.</td></tr>
            )}
            {sections.map((s) => (
              <tr key={s.section} style={{ borderBottom: '1px solid var(--hairline)' }}>
                <td style={{ padding: '8px 10px' }}>{s.section}</td>
                <td style={{ padding: '8px 10px' }}>{s.pdf_subtotal.toLocaleString('en-ZA')}</td>
                <td style={{ padding: '8px 10px' }}>{s.dxf_subtotal.toLocaleString('en-ZA')}</td>
                <td style={{ padding: '8px 10px' }}>{s.delta_zar.toLocaleString('en-ZA')}</td>
                <td style={{ padding: '8px 10px' }}>{s.delta_pct != null ? `${(s.delta_pct * 100).toFixed(1)}%` : '—'}</td>
                <td style={{ padding: '8px 10px' }}>{s.items_in_both}</td>
                <td style={{ padding: '8px 10px' }}>{s.items_only_in_pdf.length}</td>
                <td style={{ padding: '8px 10px' }}>{s.items_only_in_dxf.length}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {cmp.field_disagreements?.length > 0 && (
        <>
          <h3 style={{ fontSize: 16, marginBottom: 10 }}>Field disagreements ({cmp.field_disagreements.length})</h3>
          <ul style={{ fontSize: 13, color: 'var(--ink-2)', marginBottom: 'var(--space-lg)', paddingLeft: 18 }}>
            {cmp.field_disagreements.slice(0, 20).map((fd) => (
              <li key={fd.field_path}>
                {fd.field_path}: PDF {fd.pdf_value ?? '—'} vs DXF {fd.dxf_value ?? '—'} {fd.note && `— ${fd.note}`}
              </li>
            ))}
          </ul>
        </>
      )}

      {onDownloadPdf && (
        <button onClick={onDownloadPdf} className="btn-ghost" style={{ fontSize: 14 }}>
          Download comparison report (PDF)
        </button>
      )}
    </div>
  );
}
