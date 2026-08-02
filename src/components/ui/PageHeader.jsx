/* Shared page title + subtitle block — was hand-rolled inline (with
   subtly different spacing) on Welcome, Upload, Extraction, Compare, Boq. */
export default function PageHeader({ eyebrow, title, subtitle }) {
  return (
    <div style={{ marginBottom: 'var(--space-lg)' }}>
      {eyebrow && (
        <div style={{ fontFamily: 'var(--mono)', fontSize: 12, letterSpacing: '0.12em', color: 'var(--circuit-2)', marginBottom: 10 }}>
          {eyebrow}
        </div>
      )}
      <h1 style={{ fontSize: 'var(--text-xl)', marginBottom: subtitle ? 10 : 0 }}>{title}</h1>
      {subtitle && <p style={{ fontSize: 14, color: 'var(--ink-muted)', margin: 0 }}>{subtitle}</p>}
    </div>
  );
}
