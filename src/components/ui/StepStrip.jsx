/* Extracted from Landing.jsx's inline STEPS.map(...) block — a numbered
   "how it works" step. */
export default function StepStrip({ n, title, body }) {
  return (
    <div>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--ink-muted)', marginBottom: 6 }}>STEP {n}</div>
      <h3 style={{ fontSize: 16, marginBottom: 6 }}>{title}</h3>
      <p style={{ fontSize: 13, color: 'var(--ink-muted)', margin: 0 }}>{body}</p>
    </div>
  );
}
