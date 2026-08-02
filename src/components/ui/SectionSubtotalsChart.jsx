/* Section subtotals as horizontal bars — the original Streamlit page
   rendered this via st.bar_chart(section_subtotals_short); hand-rolled
   here with plain divs (no charting library) rather than SVG, since a
   short horizontal bar list doesn't need axis/tick measurement. */
export default function SectionSubtotalsChart({ subtotals }) {
  const entries = Object.entries(subtotals || {}).filter(([, v]) => v > 0);
  if (!entries.length) return null;
  const max = Math.max(...entries.map(([, v]) => v));

  return (
    <div className="glass-card" style={{ padding: 'var(--space-md)', marginBottom: 'var(--space-lg)' }}>
      {entries.map(([label, value]) => (
        <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
          <div style={{ width: 130, fontSize: 12, color: 'var(--ink-muted)', flexShrink: 0 }}>{label}</div>
          <div style={{ flex: 1, background: 'rgba(255,255,255,0.04)', borderRadius: 4, overflow: 'hidden', height: 18 }}>
            <div style={{ width: `${(value / max) * 100}%`, background: 'var(--gradient-primary)', height: '100%', borderRadius: 4 }} />
          </div>
          <div style={{ width: 90, fontSize: 12, color: 'var(--ink-2)', textAlign: 'right', flexShrink: 0 }}>
            R {value.toLocaleString('en-ZA', { maximumFractionDigits: 0 })}
          </div>
        </div>
      ))}
    </div>
  );
}
