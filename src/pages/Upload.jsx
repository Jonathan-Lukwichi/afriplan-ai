import { useState } from 'react';
import { api } from '../api/client';

/* DXF and PDF branches (Phase 4/5). The "Both, compare" option is Phase 6 —
   this file gets that third choice then, not a rewrite of the upload flow. */
export default function Upload({ onNavigate, onRunCreated }) {
  const [pipeline, setPipeline] = useState('dxf');
  const [files, setFiles] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const submit = async () => {
    if (!files.length) return;
    setBusy(true);
    setError(null);
    try {
      const { run_id } = await api.runs.create(files, pipeline);
      onRunCreated(run_id);
      onNavigate('extraction');
    } catch (e) {
      setError(e.message || 'Upload failed');
      setBusy(false);
    }
  };

  const selectPipeline = (p) => {
    setPipeline(p);
    setFiles([]);
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--paper)' }}>
      <div style={{ maxWidth: 640, margin: '0 auto', padding: 'var(--space-xl) var(--space-md)' }}>
        <h1 style={{ fontSize: 'var(--text-xl)', marginBottom: 10 }}>Upload a drawing</h1>
        <p style={{ fontSize: 14, color: 'var(--ink-muted)', marginBottom: 'var(--space-md)' }}>
          Run both a DXF and a PDF, then compare — coming in a later phase.
        </p>

        <div style={{ display: 'flex', gap: 10, marginBottom: 'var(--space-md)' }}>
          {[
            { id: 'dxf', label: 'DXF / DWG' },
            { id: 'pdf', label: 'PDF drawing set' },
          ].map((opt) => (
            <button
              key={opt.id}
              onClick={() => selectPipeline(opt.id)}
              style={{
                padding: '8px 16px', borderRadius: 'var(--radius-sm)', fontSize: 14, fontWeight: 600,
                cursor: 'pointer', minHeight: 40,
                background: pipeline === opt.id ? 'var(--blueprint)' : 'transparent',
                color: pipeline === opt.id ? 'white' : 'var(--blueprint)',
                border: '1px solid var(--blueprint)',
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {pipeline === 'dxf' ? (
          <input
            type="file"
            accept=".dxf,.dwg"
            onChange={(e) => setFiles(e.target.files?.[0] ? [e.target.files[0]] : [])}
            style={{ marginBottom: 'var(--space-md)', display: 'block' }}
          />
        ) : (
          <input
            type="file"
            accept=".pdf"
            multiple
            onChange={(e) => setFiles(Array.from(e.target.files || []))}
            style={{ marginBottom: 'var(--space-md)', display: 'block' }}
          />
        )}

        {error && <p style={{ color: 'var(--rose)', fontSize: 14 }}>{error}</p>}

        <button
          onClick={submit}
          disabled={!files.length || busy}
          style={{
            padding: '12px 26px', background: !files.length || busy ? 'var(--ink-muted)' : 'var(--blueprint)',
            color: 'white', border: 'none', borderRadius: 'var(--radius-sm)', fontSize: 15,
            fontWeight: 600, cursor: !files.length || busy ? 'not-allowed' : 'pointer', minHeight: 44,
          }}
        >
          {busy ? 'Uploading…' : `Run ${pipeline.toUpperCase()} pipeline →`}
        </button>
      </div>
    </div>
  );
}
