/* Section subtotals as horizontal bars — the original Streamlit page
   rendered this via st.bar_chart(section_subtotals_short); hand-rolled
   here with plain divs (no charting library) rather than SVG, since a
   short horizontal bar list doesn't need axis/tick measurement. */
export default function SectionSubtotalsChart({ subtotals }) {
  const entries = Object.entries(subtotals || {}).filter(([, v]) => v > 0);
  if (!entries.length) return null;
  const max = Math.max(...entries.map(([, v]) => v));

  return (
    <div style={{ marginBottom: 'var(--space-lg)' }}>
      {entries.map(([label, value]) => (
        <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
          <div style={{ width: 130, fontSize: 12, color: 'var(--ink-muted)', flexShrink: 0 }}>{label}</div>
          <div style={{ flex: 1, background: 'var(--paper-2)', borderRadius: 4, overflow: 'hidden', height: 18 }}>
            <div style={{ width: `${(value / max) * 100}%`, background: 'var(--blueprint)', height: '100%' }} />
          </div>
          <div style={{ width: 90, fontSize: 12, color: 'var(--ink-2)', textAlign: 'right', flexShrink: 0 }}>
            R {value.toLocaleString('en-ZA', { maximumFractionDigits: 0 })}
          </div>
        </div>
      ))}
    </div>
  );
}
