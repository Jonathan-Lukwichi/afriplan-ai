/* Numbered "how it works" step — gradient circle badge instead of a bare
   mono label, matching the reference's numbered-step treatment. */
export default function StepStrip({ n, title, body }) {
  return (
    <div>
      <div style={{
        width: 32, height: 32, borderRadius: '50%', background: 'var(--gradient-primary)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: 'var(--mono)', fontSize: 13, fontWeight: 700, color: '#05070F', marginBottom: 12,
      }}>
        {n}
      </div>
      <h3 style={{ fontSize: 16, marginBottom: 6 }}>{title}</h3>
      <p style={{ fontSize: 13, color: 'var(--ink-muted)', margin: 0 }}>{body}</p>
    </div>
  );
}
