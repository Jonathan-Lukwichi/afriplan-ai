import { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import PipelineStatusCard from '../components/ui/PipelineStatusCard';
import LegendPanel from '../components/ui/LegendPanel';
import PageHeader from '../components/ui/PageHeader';
import EmptyState from '../components/ui/EmptyState';

/* Polls the keyed run cache every 2s until the job resolves — the same
   /last-pattern spirit as the original app's materialized results, just
   keyed by run_id instead of a single global slot (see core/run_store.py).
   PDF branch (Phase 5) and the "Both" comparison view (Phase 6) extend this
   same page; it doesn't get rebuilt from scratch. */
export default function Extraction({ runId, onNavigate }) {
  const [run, setRun] = useState(null);
  const [error, setError] = useState(null);
  const timerRef = useRef(null);

  useEffect(() => {
    if (!runId) return;
    let cancelled = false;

    const poll = async () => {
      try {
        const data = await api.runs.get(runId);
        if (cancelled) return;
        setRun(data);
        if (data.status === 'running') {
          timerRef.current = setTimeout(poll, 2000);
        }
      } catch (e) {
        if (!cancelled) setError(e.message || 'Could not load this run');
      }
    };
    poll();

    return () => {
      cancelled = true;
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [runId]);

  if (!runId) {
    return <EmptyState message="No run selected." actionLabel="Upload a drawing" onAction={() => onNavigate('upload')} />;
  }

  const boq = run?.result?.boq;
  const summary = boq ? [
    { label: 'Line items', value: boq.total_items },
    { label: 'Gaps flagged', value: boq.gaps?.length ?? 0 },
    { label: 'Total incl. VAT', value: `R ${boq.total_incl_vat_zar.toLocaleString('en-ZA', { maximumFractionDigits: 0 })}` },
  ] : null;

  return (
    <div style={{ minHeight: '100vh', background: 'var(--paper)' }}>
      <div style={{ maxWidth: 720, margin: '0 auto', padding: 'var(--space-xl) var(--space-md)' }}>
        <PageHeader title="Extraction" />

        {error && <p style={{ color: 'var(--rose)' }}>{error}</p>}

        {run && (
          <PipelineStatusCard
            pipeline={run.pipeline}
            status={run.status}
            inputFile={run.input_file}
            error={run.error}
            summary={summary}
          />
        )}

        {run?.status === 'passed' && <LegendPanel legend={run.result?.legend} />}

        {run?.status === 'passed' && (
          <button
            onClick={() => onNavigate('boq')}
            style={{
              marginTop: 'var(--space-lg)', padding: '12px 26px', background: 'var(--blueprint)',
              color: 'white', border: 'none', borderRadius: 'var(--radius-sm)', fontSize: 15,
              fontWeight: 600, cursor: 'pointer', minHeight: 44,
            }}
          >
            View Bill of Quantities →
          </button>
        )}

        {run?.status === 'failed' && (
          <button
            onClick={() => onNavigate('upload')}
            style={{ marginTop: 'var(--space-lg)', padding: '12px 26px', background: 'transparent', color: 'var(--blueprint)', border: '1px solid var(--blueprint)', borderRadius: 'var(--radius-sm)', fontSize: 15, fontWeight: 600, cursor: 'pointer', minHeight: 44 }}
          >
            Try another drawing
          </button>
        )}
      </div>
    </div>
  );
}
