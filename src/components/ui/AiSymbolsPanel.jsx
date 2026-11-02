import { useEffect, useState } from 'react';
import { api } from '../../api/client';

/* Symbols recognised (ADR-0007): one picture per repeated shape, how many copies the drawings
   contain (counted exactly by geometry) and what the shape was named as: by the drawing's own
   legend, else by AI. A person can correct a name; it is remembered and used — free — on every
   later run. */
const NAMED_BY = { person: '(named by you)', legend: '(named by the legend)', ai: '(named by AI)' };

export default function AiSymbolsPanel({ result }) {
  const symbols = result?.ai_symbols || [];
  const [choices, setChoices] = useState([]);
  const [names, setNames] = useState({});
  const [saved, setSaved] = useState({});

  useEffect(() => {
    if (symbols.length) api.symbols.choices().then((r) => setChoices(r.choices)).catch(() => {});
  }, [symbols.length]);

  if (!symbols.length) return null;
  const sorted = [...symbols].sort((a, b) => b.count - a.count);

  const save = async (s) => {
    const item = names[s.signature] ?? s.item;
    try {
      await api.symbols.name(s.signature, item);
      setSaved((v) => ({ ...v, [s.signature]: true }));
    } catch {
      setSaved((v) => ({ ...v, [s.signature]: 'error' }));
    }
  };

  return (
    <div className="glass-card" style={{ padding: 'var(--space-md)', marginTop: 'var(--space-lg)' }} data-testid="ai-symbols-panel">
      <h3 style={{ fontSize: 16, margin: '0 0 6px' }}>Symbols recognised ({symbols.length} shapes)</h3>
      <p style={{ fontSize: 13, color: 'var(--ink-muted)', margin: '0 0 12px' }}>
        Every copy of a shape was counted exactly by the app. Its name comes from the row beside it in the drawing's
        legend, or from the AI when no row matches{result.ai_cost_zar ? ` (cost R ${result.ai_cost_zar.toFixed(2)})` : ''}. If a name is wrong, pick the right
        one and save — it is remembered. Run the drawings again to update the bill (remembered names cost nothing).
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))', gap: 12 }}>
        {sorted.map((s) => (
          <div key={s.signature} className="glass-card" style={{ padding: 10 }}>
            <img alt={`symbol drawn ${s.count} times`} src={`data:image/png;base64,${s.image_png_b64}`}
                 style={{ width: 96, height: 96, objectFit: 'contain', background: '#fff', borderRadius: 4, display: 'block' }} />
            <div style={{ fontSize: 13, margin: '6px 0' }}>
              <strong>× {s.count}</strong>{' '}
              <span style={{ color: 'var(--ink-muted)' }}>{NAMED_BY[s.named_by] || NAMED_BY.ai}</span>
            </div>
            <select value={names[s.signature] ?? s.item}
                    onChange={(e) => { setNames((v) => ({ ...v, [s.signature]: e.target.value })); setSaved((v) => ({ ...v, [s.signature]: false })); }}
                    style={{ width: '100%', minHeight: 36, fontSize: 13 }} aria-label="What this symbol is">
              {(choices.length ? choices : [s.item]).map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <button onClick={() => save(s)} className="btn-ghost" style={{ marginTop: 6, fontSize: 13, minHeight: 36, width: '100%' }}>
              {saved[s.signature] === true ? 'Saved ✓' : saved[s.signature] === 'error' ? 'Could not save — retry' : 'Save name'}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
