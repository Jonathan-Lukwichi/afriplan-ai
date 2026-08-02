import ValueCard from '../components/ui/ValueCard';
import StepStrip from '../components/ui/StepStrip';

/* Public marketing page — new for the FastAPI+React rewrite. AfriPlan's
   original Streamlit app had no public landing page (pages/0_Welcome.py is
   an in-wizard step behind no auth at all). Value-card copy below is drawn
   directly from that page's existing text, restyled with the ported
   blueprint design tokens rather than invented fresh. */
const VALUE_CARDS = [
  { icon: '⚡', title: 'Zero-cost DXF extraction', body: 'Deterministic CAD parsing — exact block counts, exact cable lengths, R 0.00 per run.' },
  { icon: '🤖', title: 'AI-powered PDF reading', body: 'A vision estimator reads schedules, notes, and single-line diagrams a CAD parser can\'t.' },
  { icon: '🏗️', title: 'SANS-compliant BOQ output', body: 'Every bill checked against SANS 10142-1:2017 — circuit limits, ELCB requirements, spare-way margins.' },
  { icon: '📊', title: 'Dual-pipeline cross-check', body: 'Run both pipelines and see exactly where they agree, where they disagree, and which matches your baseline.' },
];

const STEPS = [
  { n: 1, title: 'Upload', body: 'A PDF drawing set, a DXF/DWG export, or both.' },
  { n: 2, title: 'Extract', body: 'Each pipeline runs independently — see results as they land.' },
  { n: 3, title: 'Compare', body: 'If you ran both, see the real section-by-section diff.' },
  { n: 4, title: 'Export BOQ', body: 'Tender-grade Excel and PDF, priced, ready to send.' },
];

export default function Landing({ onNavigate }) {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--paper)' }}>
      <div style={{
        maxWidth: 1100, margin: '0 auto',
        padding: 'var(--space-xl) var(--space-md)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-xl)' }}>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 13, letterSpacing: '0.12em', color: 'var(--blueprint)', fontWeight: 600 }}>
            AFRIPLAN ELECTRICAL
          </div>
          <button
            onClick={() => onNavigate('login')}
            style={{ padding: '8px 18px', background: 'transparent', color: 'var(--blueprint)', border: '1px solid var(--blueprint)', borderRadius: 'var(--radius-sm)', fontSize: 14, fontWeight: 600, cursor: 'pointer', minHeight: 40 }}
          >
            Sign in
          </button>
        </div>

        <div style={{ fontFamily: 'var(--mono)', fontSize: 12, letterSpacing: '0.14em', color: 'var(--circuit-2)', marginBottom: 12 }}>
          DUAL-PIPELINE · SOUTH AFRICAN ELECTRICAL STANDARD
        </div>
        <h1 style={{ fontSize: 'var(--text-2xl)', lineHeight: 1.08, maxWidth: 780, marginBottom: 20 }}>
          Tender-grade electrical <em style={{ color: 'var(--blueprint)', fontStyle: 'italic' }}>Bills of Quantities</em>, extracted from your drawings.
        </h1>
        <p style={{ fontSize: 'var(--text-lg)', color: 'var(--ink-2)', maxWidth: 640, marginBottom: 'var(--space-lg)' }}>
          Upload an electrical PDF, a DXF, or both. Get a SANS 10142-1:2017-checked
          Bill of Quantities — priced, exportable, ready for tender.
        </p>
        <button
          onClick={() => onNavigate('login')}
          style={{
            padding: '14px 28px', background: 'var(--blueprint)', color: 'white',
            border: 'none', borderRadius: 'var(--radius-sm)', fontSize: 16,
            fontWeight: 600, cursor: 'pointer', minHeight: 44,
          }}
        >
          Start your BOQ →
        </button>

        <div style={{ borderTop: '1px solid var(--hairline-2)', margin: 'var(--space-xl) 0' }} />

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 'var(--space-md)', marginBottom: 'var(--space-xl)' }}>
          {VALUE_CARDS.map((c) => (
            <ValueCard key={c.title} icon={c.icon} title={c.title} body={c.body} />
          ))}
        </div>

        <div style={{ fontFamily: 'var(--mono)', fontSize: 12, letterSpacing: '0.14em', color: 'var(--circuit-2)', marginBottom: 8 }}>
          HOW IT WORKS
        </div>
        <h2 style={{ fontSize: 'var(--text-xl)', marginBottom: 'var(--space-lg)' }}>Four steps from drawing to tender.</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--space-md)' }}>
          {STEPS.map((s) => (
            <StepStrip key={s.n} n={s.n} title={s.title} body={s.body} />
          ))}
        </div>

        <div style={{ textAlign: 'center', marginTop: 'var(--space-xl)', paddingTop: 'var(--space-lg)', borderTop: '1px solid var(--hairline-2)', fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.1em', color: 'var(--ink-muted)' }}>
          AFRIPLAN ELECTRICAL · DUAL-PIPELINE · SANS 10142-1:2017
        </div>
      </div>
    </div>
  );
}
