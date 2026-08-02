import { useState } from 'react';
import { api } from '../api/client';

// Native file inputs render a short (~21px) hit box by default in most
// browsers, under the WCAG 2.5.8 24px AA floor — caught by the responsive
// E2E harness. minHeight + padding fixes the actual clickable box height.
const fileInputStyle = { display: 'block', minHeight: 44, padding: '10px 0', boxSizing: 'border-box' };

const PIPELINES = [
  { id: 'dxf', label: 'DXF / DWG' },
  { id: 'pdf', label: 'PDF drawing set' },
  { id: 'both', label: 'Both, compare' },
];

export default function Upload({ onNavigate, onRunCreated, onCompareCreated }) {
  const [pipeline, setPipeline] = useState('dxf');
  const [files, setFiles] = useState([]);       // dxf: [File]; pdf: [File, ...]
  const [dxfFile, setDxfFile] = useState(null); // both: the one DXF
  const [pdfFiles, setPdfFiles] = useState([]); // both: one-or-more PDFs
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const ready = pipeline === 'both' ? (dxfFile && pdfFiles.length) : files.length;

  const submit = async () => {
    if (!ready) return;
    setBusy(true);
    setError(null);
    try {
      if (pipeline === 'both') {
        const { compare_id } = await api.compare.create(dxfFile, pdfFiles);
        onCompareCreated(compare_id);
        onNavigate('compare');
      } else {
        const { run_id } = await api.runs.create(files, pipeline);
        onRunCreated(run_id);
        onNavigate('extraction');
      }
    } catch (e) {
      setError(e.message || 'Upload failed');
      setBusy(false);
    }
  };

  const selectPipeline = (p) => {
    setPipeline(p);
    setFiles([]);
    setDxfFile(null);
    setPdfFiles([]);
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--paper)' }}>
      <div style={{ maxWidth: 640, margin: '0 auto', padding: 'var(--space-xl) var(--space-md)' }}>
        <h1 style={{ fontSize: 'var(--text-xl)', marginBottom: 10 }}>Upload a drawing</h1>
        <p style={{ fontSize: 14, color: 'var(--ink-muted)', marginBottom: 'var(--space-md)' }}>
          Run a DXF, a PDF drawing set, or both — and see exactly where the
          two pipelines agree, where they disagree, and by how much.
        </p>

        <div style={{ display: 'flex', gap: 10, marginBottom: 'var(--space-md)', flexWrap: 'wrap' }}>
          {PIPELINES.map((opt) => (
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

        {pipeline === 'dxf' && (
          <input
            type="file"
            accept=".dxf,.dwg"
            onChange={(e) => setFiles(e.target.files?.[0] ? [e.target.files[0]] : [])}
            style={{ ...fileInputStyle, marginBottom: 'var(--space-md)' }}
          />
        )}

        {pipeline === 'pdf' && (
          <input
            type="file"
            accept=".pdf"
            multiple
            onChange={(e) => setFiles(Array.from(e.target.files || []))}
            style={{ ...fileInputStyle, marginBottom: 'var(--space-md)' }}
          />
        )}

        {pipeline === 'both' && (
          <div style={{ marginBottom: 'var(--space-md)' }}>
            <label style={{ fontSize: 13, color: 'var(--ink-muted)', display: 'block', marginBottom: 4 }}>DXF / DWG</label>
            <input
              type="file"
              accept=".dxf,.dwg"
              onChange={(e) => setDxfFile(e.target.files?.[0] || null)}
              style={{ ...fileInputStyle, marginBottom: 12 }}
            />
            <label style={{ fontSize: 13, color: 'var(--ink-muted)', display: 'block', marginBottom: 4 }}>PDF drawing set</label>
            <input
              type="file"
              accept=".pdf"
              multiple
              onChange={(e) => setPdfFiles(Array.from(e.target.files || []))}
              style={fileInputStyle}
            />
          </div>
        )}

        {error && <p style={{ color: 'var(--rose)', fontSize: 14 }}>{error}</p>}

        <button
          onClick={submit}
          disabled={!ready || busy}
          style={{
            padding: '12px 26px', background: !ready || busy ? 'var(--ink-muted)' : 'var(--blueprint)',
            color: 'white', border: 'none', borderRadius: 'var(--radius-sm)', fontSize: 15,
            fontWeight: 600, cursor: !ready || busy ? 'not-allowed' : 'pointer', minHeight: 44,
          }}
        >
          {busy ? 'Uploading…' : pipeline === 'both' ? 'Run both, compare →' : `Run ${pipeline.toUpperCase()} pipeline →`}
        </button>
      </div>
    </div>
  );
}
