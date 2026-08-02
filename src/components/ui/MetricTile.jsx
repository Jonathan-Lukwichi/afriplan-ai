/* Shared headline-number tile — was duplicated as an inline `Metric`
   function in both Boq.jsx and ComparisonPanel.jsx; consolidated per the
   frontend-design-system skill's "one canonical primitive, no bespoke
   markup" rule. */
export default function MetricTile({ label, value }) {
  return (
    <div>
      <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--ink)' }}>{value}</div>
      <div style={{ fontSize: 12, color: 'var(--ink-muted)' }}>{label}</div>
    </div>
  );
}
