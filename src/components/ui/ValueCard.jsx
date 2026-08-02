/* Extracted from Landing.jsx's inline VALUE_CARDS.map(...) block — the
   icon/title/body feature-card pattern, spec'd as its own component in the
   design-system inventory even though it currently has one caller. */
export default function ValueCard({ icon, title, body }) {
  return (
    <div style={{ border: '1px solid var(--hairline-2)', borderRadius: 'var(--radius-md)', padding: 'var(--space-md)', background: 'var(--paper-2)' }}>
      <div style={{ fontSize: 28, marginBottom: 10 }}>{icon}</div>
      <h3 style={{ fontSize: 17, marginBottom: 8 }}>{title}</h3>
      <p style={{ fontSize: 14, color: 'var(--ink-muted)', margin: 0, lineHeight: 1.5 }}>{body}</p>
    </div>
  );
}
