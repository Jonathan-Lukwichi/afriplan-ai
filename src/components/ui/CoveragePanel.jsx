import { useEffect, useState } from 'react';
import { api } from '../../api/client';

/* Drawing coverage (GET /api/audit/coverage/{run}) — which item types this
   upload can quantify, and which drawing to send next for a complete BOQ.
   Items without supporting drawings stay PROVISIONAL, never silent. */
export default function CoveragePanel({ runId }) {
  const [cov, setCov] = useState(null);

  useEffect(() => {
    if (!runId) return;
    api.audit.coverage(runId).then(setCov).catch(() => setCov(null));
  }, [runId]);

  if (!cov) return null;
  const requests = Object.entries(cov.requests || {});

  return (
    <div className="glass-card" style={{ padding: 'var(--space-md)', marginTop: 'var(--space-lg)' }} data-testid="coverage-panel">
      <h3 style={{ fontSize: 16, margin: '0 0 8px' }}>
        Drawing coverage — {cov.reproducible_families.length} item types supported
        {requests.length ? ` · ${requests.length} drawing type(s) missing` : ''}
      </h3>
      <p style={{ fontSize: 13, color: 'var(--ink-muted)', margin: '0 0 10px' }}>
        Recognised: {cov.uploaded_names.length ? cov.uploaded_names.join(', ') : 'no drawing type recognised'}
      </p>
      {requests.length ? (
        <ul style={{ fontSize: 13, margin: 0, paddingLeft: 18 }}>
          {requests.map(([d, fams]) => (
            <li key={d} style={{ marginBottom: 6 }}>
              <strong>Add a {cov.request_names[d] || d}</strong> to unlock:{' '}
              {fams.slice(0, 10).map((f) => f.replaceAll('_', ' ')).join(', ')}{fams.length > 10 ? '…' : ''}
            </li>
          ))}
        </ul>
      ) : (
        <p style={{ fontSize: 13, color: 'var(--emerald)', margin: 0 }}>All drawing-derived items are supported by this upload.</p>
      )}
    </div>
  );
}
