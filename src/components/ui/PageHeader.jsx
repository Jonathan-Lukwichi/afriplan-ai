/* Shared page title + subtitle block — was hand-rolled inline (with
   subtly different spacing) on Welcome, Upload, Extraction, Compare, Boq. */
export default function PageHeader({ eyebrow, title, subtitle }) {
  return (
    <div style={{ marginBottom: 'var(--space-md)' }}>
      {eyebrow && (
        <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--ink-muted)', marginBottom: 6 }}>
          {eyebrow}
        </div>
      )}
      <h1 style={{ fontSize: 'clamp(1.75rem, 2.6vw, 2.25rem)', marginBottom: subtitle ? 8 : 0 }}>{title}</h1>
      {subtitle && <p style={{ fontSize: 15, lineHeight: 1.55, color: 'var(--ink-2)', margin: 0, maxWidth: '72ch' }}>{subtitle}</p>}
    </div>
  );
}
