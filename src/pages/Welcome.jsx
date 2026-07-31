/* In-app landing, post-login — NOT the public marketing page. AfriPlan's
   original pages/0_Welcome.py is this same in-wizard orientation step (kept
   as a naming pattern deliberately, per CLAUDE.md); the public Landing.jsx
   is a separate new page. */
export default function Welcome({ onNavigate }) {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--paper)' }}>
      <div style={{ maxWidth: 720, margin: '0 auto', padding: 'var(--space-xl) var(--space-md)' }}>
        <div style={{ fontFamily: 'var(--mono)', fontSize: 12, letterSpacing: '0.12em', color: 'var(--circuit-2)', marginBottom: 12 }}>
          AFRIPLAN ELECTRICAL
        </div>
        <h1 style={{ fontSize: 'var(--text-xl)', marginBottom: 14 }}>Start a new Bill of Quantities</h1>
        <p style={{ fontSize: 15, color: 'var(--ink-2)', marginBottom: 'var(--space-lg)' }}>
          Upload a drawing and we'll run it through the DXF pipeline — a
          deterministic, zero-cost parser that reads block counts, circuits
          and cable lengths straight off the CAD geometry.
        </p>
        <button
          onClick={() => onNavigate('upload')}
          style={{
            padding: '14px 28px', background: 'var(--blueprint)', color: 'white',
            border: 'none', borderRadius: 'var(--radius-sm)', fontSize: 16,
            fontWeight: 600, cursor: 'pointer', minHeight: 44,
          }}
        >
          Upload a drawing →
        </button>
      </div>
    </div>
  );
}
