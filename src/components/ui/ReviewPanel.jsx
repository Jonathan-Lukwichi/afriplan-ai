import { useState } from 'react';
import { api } from '../../api/client';

/* "Things to check" as questions: a person answers one, the bill updates, and the answer can be
   undone. What the reader found is never changed, so accuracy stays a measure of the reader. Each
   group opens into its questions; a one-click answer covers the easy groups. */
const rand = (v) => `R ${Math.round(v).toLocaleString('en-ZA')}`;
const signed = (v) => `${v < 0 ? '−' : '+'}${rand(Math.abs(v))}`;
const COLOR = { high: 'var(--rose)', medium: 'var(--amber)', low: 'var(--ink-muted)' };
const inputStyle = {
  width: 130, padding: 8, background: 'rgba(255,255,255,0.03)', border: '1px solid var(--hairline-2)',
  borderRadius: 'var(--radius-sm)', color: 'var(--ink)', fontSize: 14,
};

function worth(q) {
  const parts = [];
  if (q.on_bill_zar) parts.push(`${rand(q.on_bill_zar)} on the bill`);
  if (q.per_unit_zar) parts.push(`${rand(q.per_unit_zar)} per ${q.per_unit}`);
  return parts.join(' · ');
}

function Question({ q, busy, onSave, onUndo }) {
  const start = () => Object.fromEntries(q.fields.map((f) => [f.name, q.answer?.values?.[f.name] ?? f.value ?? '']));
  const [draft, setDraft] = useState(start);
  const set = (name, value) => setDraft((d) => ({ ...d, [name]: value }));
  const save = () => onSave(q, Object.fromEntries(
    Object.entries(draft).filter(([, v]) => v !== '').map(([k, v]) => [k, Number(v)])));

  return (
    <div style={{ padding: '12px 0', borderTop: '1px solid var(--hairline-2)' }} data-testid={`question-${q.id}`}>
      <div style={{ fontSize: 14, fontWeight: 600, color: COLOR[q.severity] && q.status === 'open' ? COLOR[q.severity] : 'var(--ink)' }}>
        {q.title}
      </div>
      {q.why && <div style={{ fontSize: 13, color: 'var(--ink-muted)' }}>What the app did: {q.why}</div>}
      {worth(q) && <div style={{ fontSize: 13 }} data-testid="question-worth">{worth(q)}</div>}

      {q.status === 'recheck' && (
        <p style={{ fontSize: 13, color: 'var(--amber)', margin: '6px 0 0' }}>
          Given on an earlier drawing, so it is not in the bill. Please confirm it still holds.
        </p>
      )}

      {q.options.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
          {q.options.map((o) => (
            <button key={o.label} type="button" className="btn-ghost" style={{ fontSize: 13, minHeight: 36 }}
                    onClick={() => set('length_m', o.value)}>
              {o.label}: {o.value} m ({signed(o.change_zar)})
            </button>
          ))}
        </div>
      )}

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'flex-end', marginTop: 8 }}>
        {q.fields.map((f) => (
          <label key={f.name} style={{ fontSize: 13, color: 'var(--ink-muted)' }}>
            <span style={{ display: 'block', marginBottom: 4 }}>{f.label}{f.unit ? ` (${f.unit})` : ''}</span>
            <input type="number" min="0" step="any" value={draft[f.name]} style={inputStyle}
                   onChange={(e) => set(f.name, e.target.value)} />
          </label>
        ))}
        <button type="button" className="btn-ghost" disabled={busy} onClick={save} style={{ fontSize: 13, minHeight: 36 }}>
          {q.fields.length ? (q.status === 'answered' ? 'Update answer' : 'Save answer') : 'Confirm'}
        </button>
        {q.status !== 'open' && (
          <button type="button" className="btn-ghost" disabled={busy} onClick={() => onUndo(q)} style={{ fontSize: 13, minHeight: 36 }}>
            Undo
          </button>
        )}
        {q.status === 'answered' && (
          <span style={{ fontSize: 13, color: 'var(--emerald)' }}>Answered by {q.answer.by}</span>
        )}
      </div>
    </div>
  );
}

export default function ReviewPanel({ runId, review, onChange }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const run = async (work) => {
    setBusy(true);
    setError(null);
    try {
      onChange(await work());
    } catch (e) {
      setError(e.message || 'Could not save that answer');
    } finally {
      setBusy(false);
    }
  };
  const save = (q, values) => run(() => api.review.answer(runId, q.id, values));
  const undo = (q) => run(() => api.review.undo(runId, q.id));
  const bulk = (g) => run(async () => {
    let last = review;
    for (const q of g.questions.filter((x) => x.status !== 'answered')) {
      last = await api.review.answer(runId, q.id, g.bulk.values);
    }
    return last;
  });

  return (
    <>
      <h3 style={{ fontSize: 16, marginBottom: 4 }}>Things to check — {review.open}</h3>
      <p style={{ fontSize: 13, color: 'var(--ink-muted)', margin: '0 0 10px' }}>
        {review.open
          ? 'Answer these and the bill updates. Most urgent first. Amounts are before contingency and VAT.'
          : 'Everything is answered.'}
      </p>
      {review.answered > 0 && (
        <p style={{ fontSize: 14, margin: '0 0 10px' }} data-testid="review-change">
          Your {review.answered} answer{review.answered === 1 ? '' : 's'} changed the bill by <strong>{signed(review.change_zar)}</strong>.
        </p>
      )}
      {error && <p role="alert" style={{ color: 'var(--rose)', fontSize: 14 }}>{error}</p>}

      {review.groups.map((g, i) => (
        <details key={g.key} open={i === 0} className="glass-card" style={{ padding: 'var(--space-md)', marginBottom: 'var(--space-md)' }}
                 data-testid={`group-${g.key}`}>
          <summary style={{ cursor: 'pointer', fontSize: 15, fontWeight: 600 }}>
            {g.title} — {g.open ? `${g.open} open` : 'done'}
          </summary>
          {g.bulk && g.open > 0 && (
            <button type="button" className="btn-ghost" disabled={busy} onClick={() => bulk(g)}
                    style={{ fontSize: 13, minHeight: 36, marginTop: 10 }}>
              {g.bulk.label}
            </button>
          )}
          <div style={{ marginTop: 8 }}>
            {g.questions.map((q) => (
              <Question key={`${q.id}-${q.status}`} q={q} busy={busy} onSave={save} onUndo={undo} />
            ))}
          </div>
        </details>
      ))}
    </>
  );
}
