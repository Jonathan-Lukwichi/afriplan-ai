import { useState } from 'react';
import { api } from '../api/client';

/* DXF-only for now (Phase 4). The PDF branch and the "Both" comparison
   option land in Phase 5/6 — this file gets a pipeline selector then, not a
   rewrite of the upload flow. */
export default function Upload({ onNavigate, onRunCreated }) {
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const submit = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const { run_id } = await api.runs.create(file, 'dxf');
      onRunCreated(run_id);
      onNavigate('extraction');
    } catch (e) {
      setError(e.message || 'Upload failed');
      setBusy(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--paper)' }}>
      <div style={{ maxWidth: 640, margin: '0 auto', padding: 'var(--space-xl) var(--space-md)' }}>
        <h1 style={{ fontSize: 'var(--text-xl)', marginBottom: 10 }}>Upload a drawing</h1>
        <p style={{ fontSize: 14, color: 'var(--ink-muted)', marginBottom: 'var(--space-lg)' }}>
          DXF or DWG export. PDF and dual-pipeline comparison are coming in a
          later phase of this build.
        </p>

        <input
          type="file"
          accept=".dxf,.dwg"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          style={{ marginBottom: 'var(--space-md)', display: 'block' }}
        />

        {error && <p style={{ color: 'var(--rose)', fontSize: 14 }}>{error}</p>}

        <button
          onClick={submit}
          disabled={!file || busy}
          style={{
            padding: '12px 26px', background: !file || busy ? 'var(--ink-muted)' : 'var(--blueprint)',
            color: 'white', border: 'none', borderRadius: 'var(--radius-sm)', fontSize: 15,
            fontWeight: 600, cursor: !file || busy ? 'not-allowed' : 'pointer', minHeight: 44,
          }}
        >
          {busy ? 'Uploading…' : 'Run DXF pipeline →'}
        </button>
      </div>
    </div>
  );
}
