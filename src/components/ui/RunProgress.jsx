/* Live progress of a PDF run (GET /api/runs/{id} → progress): which step, how many pages,
   how long so far, and why it is waiting when the AI provider says "busy". Without it a
   slow run on a free AI tier looks exactly like a dead one. */
const STEPS = [
  { key: 'classify', label: 'Sort pages' },
  { key: 'read', label: 'Read drawings' },
  { key: 'price', label: 'Measure & price' },
];

function elapsed(seconds) {
  const s = Math.max(0, Math.round(seconds || 0));
  const m = Math.floor(s / 60);
  return m ? `${m} min ${String(s % 60).padStart(2, '0')} s` : `${s} s`;
}

export default function RunProgress({ progress }) {
  if (!progress) return null;
  if (progress.stage === 'queued') {
    // waiting for a free slot on the server (api/core/run_queue.py) — nothing has started yet
    return (
      <div data-testid="run-progress" style={{ marginTop: 12 }}>
        <div style={{ fontSize: 14, color: 'var(--ink)', marginBottom: 6 }}>{progress.message}</div>
        <div style={{ fontSize: 12, color: 'var(--ink-muted)', fontFamily: 'var(--mono)' }}>
          waiting for {elapsed(progress.elapsed_s)}
        </div>
        {progress.note && (
          <div style={{ fontSize: 13, color: 'var(--amber)', marginTop: 8 }}>⏳ {progress.note}</div>
        )}
      </div>
    );
  }
  const current = STEPS.findIndex((s) => s.key === progress.stage);
  const pct = progress.total ? Math.round((100 * progress.done) / progress.total) : null;

  return (
    <div data-testid="run-progress" style={{ marginTop: 12 }}>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
        {STEPS.map((s, i) => {
          const state = current < 0 || i > current ? 'todo' : i < current ? 'done' : 'now';
          return (
            <span key={s.key} style={{
              fontSize: 12, padding: '3px 10px', borderRadius: 999, fontWeight: state === 'now' ? 600 : 500,
              border: '1px solid var(--hairline-2)',
              background: state === 'now' ? 'var(--blueprint)' : state === 'done' ? 'var(--paper-2)' : 'transparent',
              color: state === 'now' ? '#fff' : state === 'done' ? 'var(--ink-2)' : 'var(--ink-muted)',
            }}>
              {state === 'done' ? '✓ ' : `${i + 1}. `}{s.label}
            </span>
          );
        })}
      </div>

      <div style={{ fontSize: 14, color: 'var(--ink)', marginBottom: 6 }}>{progress.message}</div>

      {pct !== null && (
        <div role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}
             style={{ height: 8, borderRadius: 999, background: 'var(--paper-2)', overflow: 'hidden', marginBottom: 6 }}>
          <div style={{ width: `${pct}%`, height: '100%', background: 'var(--blueprint)', transition: 'width .4s' }} />
        </div>
      )}

      <div style={{ fontSize: 12, color: 'var(--ink-muted)', fontFamily: 'var(--mono)' }}>
        {pct !== null ? `${progress.done} / ${progress.total} pages · ` : ''}running for {elapsed(progress.elapsed_s)}
      </div>

      {progress.note && (
        <div style={{ fontSize: 13, color: 'var(--amber)', marginTop: 8 }}>⏳ {progress.note}</div>
      )}
    </div>
  );
}
