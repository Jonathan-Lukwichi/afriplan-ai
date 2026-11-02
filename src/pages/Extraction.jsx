import { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import { toCheck } from '../lib/plainWords';
import PipelineStatusCard from '../components/ui/PipelineStatusCard';
import LegendPanel from '../components/ui/LegendPanel';
import CoveragePanel from '../components/ui/CoveragePanel';
import ExtractionAccuracyPanel from '../components/ui/ExtractionAccuracyPanel';
import DrawingSetPanel from '../components/ui/DrawingSetPanel';
import AiSymbolsPanel from '../components/ui/AiSymbolsPanel';
import PageHeader from '../components/ui/PageHeader';
import EmptyState from '../components/ui/EmptyState';

/* Polls the keyed run cache every 2s until the job resolves — the same
   /last-pattern spirit as the original app's materialized results, just
   keyed by run_id instead of a single global slot (see core/run_store.py).
   PDF branch (Phase 5) and the "Both" comparison view (Phase 6) extend this
   same page; it doesn't get rebuilt from scratch. */
export default function Extraction({ runId, onNavigate }) {
  const [run, setRun] = useState(null);
  const [review, setReview] = useState(null);
  const [error, setError] = useState(null);
  const timerRef = useRef(null);

  useEffect(() => {
    if (run?.status !== 'passed') return;
    api.review.get(runId).then(setReview).catch(() => setReview(null));
  }, [run?.status, runId]);

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
  const total = review?.available ? review.total_incl_vat_zar : boq?.total_incl_vat_zar;
  const summary = boq ? [
    { label: 'Line items', value: boq.total_items },
    { label: 'Things to check', value: review?.available ? review.open : toCheck(boq.gaps).length },
    { label: 'Total incl. VAT', value: `R ${total.toLocaleString('en-ZA', { maximumFractionDigits: 0 })}` },
  ] : null;

  return (
    <div style={{ maxWidth: 1440, padding: 'var(--space-lg) clamp(16px, 3vw, 32px)' }}>
      <PageHeader title="Take-off" />

      {error && <p style={{ color: 'var(--rose)' }}>{error}</p>}

      {run && (
        <PipelineStatusCard
          pipeline={run.pipeline}
          status={run.status}
          inputFile={run.input_file}
          error={run.error}
          summary={summary}
          progress={run.progress}
        />
      )}

      {run?.status === 'passed' && <ExtractionAccuracyPanel runId={runId} />}

      {run?.status === 'passed' && run.pipeline === 'dxf' && <DrawingSetPanel result={run.result} />}

      {run?.status === 'passed' && run.pipeline === 'dxf' && <AiSymbolsPanel result={run.result} />}

      {run?.status === 'passed' && <LegendPanel legend={run.result?.legend} />}

      {run?.status === 'passed' && <CoveragePanel runId={runId} />}

      {run?.status === 'passed' && (
        <button onClick={() => onNavigate('boq')} className="btn-gradient" style={{ marginTop: 'var(--space-lg)', fontSize: 15 }}>
          View Bill of Quantities →
        </button>
      )}

      {run?.status === 'failed' && (
        <button onClick={() => onNavigate('upload')} className="btn-ghost" style={{ marginTop: 'var(--space-lg)', fontSize: 15 }}>
          Try another drawing
        </button>
      )}
    </div>
  );
}
