/* Shared headline-number stat card — was duplicated as an inline `Metric`
   function in both Boq.jsx and ComparisonPanel.jsx; consolidated per the
   frontend-design-system skill's "one canonical primitive, no bespoke
   markup" rule. Glass-card + gradient number, matching the Dashdark X
   reference's stat-card treatment. */
export default function MetricTile({ label, value }) {
  return (
    <div className="glass-card" style={{ padding: '16px 18px' }}>
      <div className="text-gradient" style={{ fontSize: 22, fontWeight: 800 }}>{value}</div>
      <div style={{ fontSize: 12, color: 'var(--ink-muted)', marginTop: 4 }}>{label}</div>
    </div>
  );
}
