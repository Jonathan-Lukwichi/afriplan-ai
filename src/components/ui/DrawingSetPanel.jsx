/* A DXF/DWG drawing set run as one project: what each drawing was read as, and
   which one the feeder routes were measured on (api/agent/dxf_pipeline run_dxf_project). */
const ROLE_COLOR = { 'site plan': 'var(--emerald)', SLD: 'var(--blueprint-2)', layout: 'var(--ink)', other: 'var(--ink-muted)' };

export default function DrawingSetPanel({ result }) {
  const files = result?.files || [];
  if (files.length < 2) return null;
  const sitePlan = result.site_plan_file;
  return (
    <div className="glass-card" style={{ padding: 'var(--space-md)', marginTop: 'var(--space-lg)' }} data-testid="drawing-set-panel">
      <h3 style={{ fontSize: 16, margin: '0 0 6px' }}>Drawing set ({files.length} drawings, read as one project)</h3>
      <p style={{ fontSize: 13, color: sitePlan ? 'var(--emerald)' : 'var(--amber)', margin: '0 0 12px' }}>
        {sitePlan
          ? `Feeder routes measured on ${sitePlan}: ${result.routes_measured} feeder${result.routes_measured === 1 ? '' : 's'} priced on measured lengths.`
          : 'No electrical site plan with cable routes found — feeder lengths are assumed and flagged in the gap report.'}
      </p>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ textAlign: 'left' }}>
              <th style={{ padding: '6px 8px', borderBottom: '1px solid var(--hairline-2)' }}>Drawing</th>
              <th style={{ padding: '6px 8px', borderBottom: '1px solid var(--hairline-2)' }}>Read as</th>
            </tr>
          </thead>
          <tbody>
            {files.map((f) => (
              <tr key={f.file_name} style={{ borderBottom: '1px solid var(--hairline)' }}>
                <td style={{ padding: '6px 8px', wordBreak: 'break-word' }}>{f.file_name}</td>
                <td style={{
                  padding: '6px 8px',
                  color: !f.ok ? 'var(--rose)' : f.role?.startsWith('older revision') ? 'var(--amber)' : (ROLE_COLOR[f.role] || 'var(--ink)'),
                }}>
                  {f.ok ? (f.role?.startsWith('older revision') ? `skipped — ${f.role}` : (f.role || '—')) : `could not read: ${f.error}`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
