import { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import ComparisonPanel from '../components/ui/ComparisonPanel';
import EmptyState from '../components/ui/EmptyState';

/* Polls the keyed comparison cache (core/compare_store.py) every 2s until
   both underlying runs resolve and compare_runs has fired. */
export default function Compare({ compareId, onNavigate }) {
  const [record, setRecord] = useState(null);
  const [error, setError] = useState(null);
  const timerRef = useRef(null);

  useEffect(() => {
    if (!compareId) return;
    let cancelled = false;

    const poll = async () => {
      try {
        const data = await api.compare.get(compareId);
        if (cancelled) return;
        setRecord(data);
        if (data.status === 'running') {
          timerRef.current = setTimeout(poll, 2000);
        }
      } catch (e) {
        if (!cancelled) setError(e.message || 'Could not load this comparison');
      }
    };
    poll();

    return () => {
      cancelled = true;
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [compareId]);

  if (!compareId) {
    return <EmptyState message="No comparison selected." actionLabel="Upload drawings" onAction={() => onNavigate('upload')} />;
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--paper)' }}>
      <div style={{ maxWidth: 900, margin: '0 auto', padding: 'var(--space-xl) var(--space-md)' }}>
        <h1 style={{ fontSize: 'var(--text-xl)', marginBottom: 'var(--space-md)' }}>Cross-pipeline comparison</h1>

        {error && <p style={{ color: 'var(--rose)' }}>{error}</p>}

        {record?.status === 'running' && (
          <span className="afp-tag-running" style={{ padding: '3px 10px', borderRadius: 999, fontSize: 12, fontWeight: 600 }}>
            Running both pipelines…
          </span>
        )}

        {record?.status === 'failed' && (
          <>
            <p style={{ color: 'var(--rose)' }}>{record.error}</p>
            <button
              onClick={() => onNavigate('upload')}
              style={{ marginTop: 'var(--space-md)', padding: '12px 26px', background: 'transparent', color: 'var(--blueprint)', border: '1px solid var(--blueprint)', borderRadius: 'var(--radius-sm)', fontSize: 15, fontWeight: 600, cursor: 'pointer', minHeight: 44 }}
            >
              Try again
            </button>
          </>
        )}

        {record?.status === 'passed' && record.result && (
          <ComparisonPanel
            cmp={record.result}
            onDownloadPdf={() => window.open(api.compare.pdfUrl(compareId), '_blank')}
          />
        )}
      </div>
    </div>
  );
}
