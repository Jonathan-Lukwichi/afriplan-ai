import { useState } from 'react';
import { api } from '../api/client';
import PageHeader from '../components/ui/PageHeader';

// Native file inputs render a short (~21px) hit box by default in most
// browsers, under the WCAG 2.5.8 24px AA floor — caught by the responsive
// E2E harness. minHeight + padding fixes the actual clickable box height.
const fileInputStyle = {
  display: 'block', minHeight: 44, padding: '10px 12px', boxSizing: 'border-box',
  width: '100%', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--hairline-2)',
  borderRadius: 'var(--radius-sm)', color: 'var(--ink)', fontSize: 13,
};

const PIPELINES = [
  { id: 'dxf', label: 'DXF / DWG' },
  { id: 'pdf', label: 'PDF drawing set' },
  { id: 'both', label: 'Both, compare' },
];

const PIPELINE_INFO = {
  dxf: {
    title: 'DXF engine',
    body: 'Reads the exact CAD geometry directly — fast, precise, and free to run. A .dwg file is converted to .dxf automatically first.',
  },
  pdf: {
    title: 'PDF engine',
    body: 'Uses an AI vision model to read scanned or exported pages the way a person would. Slower, with a small real cost per page.',
  },
  both: {
    title: 'Both engines',
    body: 'Runs the DXF and PDF engines on the same job independently, then shows a side-by-side comparison of where they agree and disagree.',
  },
};

const NEXT_STEPS = [
  { label: 'Take-off', desc: 'Every symbol is counted and matched to a legend.' },
  { label: 'BoQ & quotation', desc: 'Counted items become a priced, SANS-checked bill.' },
  { label: 'Pricing (optional)', desc: 'Check the rates against live supplier quotes.' },
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

  const activeInfo = PIPELINE_INFO[pipeline];

  return (
    <div style={{ maxWidth: 1440, padding: 'var(--space-xl) var(--space-md)' }}>
      <PageHeader
        title="Upload a drawing"
        subtitle="Run a DXF, a PDF drawing set, or both — and see exactly where the two engines agree, where they disagree, and by how much."
      />

      <div className="upload-grid" style={{ display: 'grid', gap: 'var(--space-lg)', alignItems: 'start' }}>
        <div className="glass-card" style={{ padding: 'var(--space-md)' }}>
          <div style={{ display: 'flex', gap: 10, marginBottom: 'var(--space-md)', flexWrap: 'wrap' }}>
            {PIPELINES.map((opt) => (
              <button
                key={opt.id}
                onClick={() => selectPipeline(opt.id)}
                className={pipeline === opt.id ? 'btn-gradient' : 'btn-ghost'}
                style={{ padding: '9px 18px', minHeight: 40, fontSize: 14 }}
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

          <button onClick={submit} disabled={!ready || busy} className="btn-gradient" style={{ fontSize: 15 }}>
            {busy ? 'Uploading…' : pipeline === 'both' ? 'Run both, compare →' : `Run ${pipeline.toUpperCase()} engine →`}
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div className="glass-card" style={{ padding: 'var(--space-md)' }}>
            <div style={{ fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--ink-muted)', marginBottom: 10 }}>
              This engine
            </div>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 6 }}>{activeInfo.title}</div>
            <p style={{ fontSize: 13, color: 'var(--ink-2)', lineHeight: 1.55, margin: 0 }}>{activeInfo.body}</p>
          </div>

          <div className="glass-card" style={{ padding: 'var(--space-md)' }}>
            <div style={{ fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--ink-muted)', marginBottom: 14 }}>
              What happens next
            </div>
            {NEXT_STEPS.map((step, i) => (
              <div key={step.label} style={{ display: 'flex', gap: 12, alignItems: 'flex-start', marginBottom: i < NEXT_STEPS.length - 1 ? 14 : 0 }}>
                <span style={{
                  fontFamily: 'var(--mono)', fontSize: 11, fontWeight: 700, color: 'var(--blueprint-2)',
                  border: '1px solid var(--hairline-2)', borderRadius: 6, width: 22, height: 22,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}>
                  {i + 1}
                </span>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 2 }}>{step.label}</div>
                  <div style={{ fontSize: 12.5, color: 'var(--ink-muted)', lineHeight: 1.5 }}>{step.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
