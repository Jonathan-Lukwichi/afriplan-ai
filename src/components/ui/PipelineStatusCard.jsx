/* Spec'd 1:1 from the original app's dead ui/pipeline_column.py: a state
   badge (running/passed/failed), a headline score, and a downloads/summary
   row. Status colors reuse the ported .afp-tag-* classes from tokens.css. */
const TAG_CLASS = {
  running: 'afp-tag-running',
  passed: 'afp-tag-pass',
  failed: 'afp-tag-fail',
};

const LABEL = {
  running: 'Running…',
  passed: 'Passed',
  failed: 'Failed',
};

export default function PipelineStatusCard({ pipeline, status, inputFile, error, summary }) {
  return (
    <div className="glass-card" style={{ padding: 'var(--space-md)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <div style={{ fontFamily: 'var(--mono)', fontSize: 12, letterSpacing: '0.1em', color: 'var(--ink-muted)' }}>
          {pipeline.toUpperCase()} ENGINE
        </div>
        <span className={TAG_CLASS[status] || 'afp-tag-idle'} style={{ padding: '3px 10px', borderRadius: 999, fontSize: 12, fontWeight: 600 }}>
          {LABEL[status] || status}
        </span>
      </div>
      <div style={{ fontSize: 14, color: 'var(--ink-2)', marginBottom: summary || error ? 10 : 0 }}>{inputFile}</div>

      {status === 'failed' && error && (
        <p style={{ fontSize: 13, color: 'var(--rose)', margin: 0 }}>{error}</p>
      )}

      {status === 'passed' && summary && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 10 }}>
          {summary.map((s) => (
            <div key={s.label}>
              <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--ink)' }}>{s.value}</div>
              <div style={{ fontSize: 12, color: 'var(--ink-muted)' }}>{s.label}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
