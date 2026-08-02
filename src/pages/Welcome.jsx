import PageHeader from '../components/ui/PageHeader';

/* In-app landing, post-login — NOT the public marketing page. AfriPlan's
   original pages/0_Welcome.py is this same in-wizard orientation step (kept
   as a naming pattern deliberately, per CLAUDE.md); the public Landing.jsx
   is a separate new page. Renders inside AppShell now — no own background/
   full-bleed wrapper needed. */
export default function Welcome({ onNavigate }) {
  return (
    <div style={{ maxWidth: 720, padding: 'var(--space-xl) var(--space-md)' }}>
      <PageHeader
        eyebrow="AFRIPLAN ELECTRICAL"
        title="Start a new Bill of Quantities"
        subtitle="Upload a drawing and we'll run it through the DXF pipeline — a deterministic, zero-cost parser that reads block counts, circuits and cable lengths straight off the CAD geometry."
      />
      <button onClick={() => onNavigate('upload')} className="btn-gradient" style={{ fontSize: 16, padding: '14px 28px' }}>
        Upload a drawing →
      </button>
    </div>
  );
}
