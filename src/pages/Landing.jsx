import { BarChart3, Cpu, ShieldCheck, Zap } from 'lucide-react';
import Navbar from '../components/ui/Navbar';
import ValueCard from '../components/ui/ValueCard';
import StepStrip from '../components/ui/StepStrip';
import heroImage from '../assets/images/hero-switchgear.jpg';
import trustImage from '../assets/images/trust-strip-site-team.jpg';

/* Public marketing page — dark "AI product" redesign (Robotiko/Dashdark X
   reference), built on AfriPlan's own blueprint-blue + circuit-cyan
   identity. Value-card copy carried over verbatim from the original
   Streamlit app's Welcome page. */
const VALUE_CARDS = [
  { icon: Zap, title: 'Zero-cost DXF extraction', body: 'Deterministic CAD parsing — exact block counts, exact cable lengths, R 0.00 per run.' },
  { icon: Cpu, title: 'AI-powered PDF reading', body: 'A vision estimator reads schedules, notes, and single-line diagrams a CAD parser can\'t.' },
  { icon: ShieldCheck, title: 'SANS-compliant BOQ output', body: 'Every bill checked against SANS 10142-1:2017 — circuit limits, ELCB requirements, spare-way margins.' },
  { icon: BarChart3, title: 'Dual-pipeline cross-check', body: 'Run both pipelines and see exactly where they agree, where they disagree, and which matches your baseline.' },
];

const STEPS = [
  { n: 1, title: 'Upload', body: 'A PDF drawing set, a DXF/DWG export, or both.' },
  { n: 2, title: 'Extract', body: 'Each pipeline runs independently — see results as they land.' },
  { n: 3, title: 'Compare', body: 'If you ran both, see the real section-by-section diff.' },
  { n: 4, title: 'Export BOQ', body: 'Tender-grade Excel and PDF, priced, ready to send.' },
];

const STATS = [
  { value: 'R 0.00', label: 'DXF pipeline cost per run' },
  { value: '2', label: 'Independent extraction pipelines' },
  { value: '10142-1', label: 'SANS standard, checked automatically' },
  { value: '5-sheet', label: 'Tender-grade export document' },
];

export default function Landing({ onNavigate }) {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--paper)', position: 'relative', overflow: 'hidden' }}>
      {/* Decorative background glow orbs */}
      <div style={glowOrb('-10%', '-10%', 'var(--glow-blue)')} />
      <div style={glowOrb('60%', '5%', 'var(--glow-cyan)')} />

      <Navbar onNavigate={onNavigate} />

      <div style={{ position: 'relative', maxWidth: 1200, margin: '0 auto', padding: '0 clamp(20px, 5vw, 64px)' }}>

        {/* ─── Hero ─────────────────────────────────────────────── */}
        <div style={{
          display: 'grid', gridTemplateColumns: '1.1fr 0.9fr', gap: 'var(--space-xl)',
          alignItems: 'center', padding: 'clamp(48px, 8vw, 96px) 0 clamp(32px, 6vw, 64px)',
        }}>
          <div>
            <div style={{ fontFamily: 'var(--mono)', fontSize: 12, letterSpacing: '0.14em', color: 'var(--circuit-2)', marginBottom: 16 }}>
              DUAL-PIPELINE · SOUTH AFRICAN ELECTRICAL STANDARD
            </div>
            <h1 style={{ fontSize: 'var(--text-2xl)', lineHeight: 1.05, marginBottom: 22 }}>
              Tender-grade electrical{' '}
              <span className="text-gradient">Bills of Quantities</span>, extracted from your drawings.
            </h1>
            <p style={{ fontSize: 'var(--text-lg)', color: 'var(--ink-2)', maxWidth: 560, marginBottom: 'var(--space-lg)', lineHeight: 1.5 }}>
              Upload an electrical PDF, a DXF, or both. Get a SANS 10142-1:2017-checked
              Bill of Quantities — priced, exportable, ready for tender.
            </p>
            <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
              <button onClick={() => onNavigate('login')} className="btn-gradient" style={{ padding: '15px 30px', fontSize: 16 }}>
                Start your BoQ →
              </button>
              <button onClick={() => onNavigate('login')} className="btn-ghost" style={{ padding: '14px 26px', fontSize: 15 }}>
                Sign in
              </button>
            </div>
          </div>

          <div style={{ position: 'relative' }}>
            <div style={{ position: 'absolute', inset: -16, background: 'var(--gradient-primary)', opacity: 0.25, filter: 'blur(40px)', borderRadius: 24 }} />
            <img
              src={heroImage} alt="Electrical switchgear room"
              style={{
                position: 'relative', width: '100%', height: 'auto', borderRadius: 'var(--radius-lg)',
                border: '1px solid var(--card-border)', boxShadow: 'var(--shadow-card)', display: 'block',
              }}
            />
          </div>
        </div>

        {/* ─── Stats strip ──────────────────────────────────────── */}
        <div className="glass-card" style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
          gap: 'var(--space-md)', padding: 'var(--space-lg)', marginBottom: 'var(--space-xl)',
        }}>
          {STATS.map((s) => (
            <div key={s.label} style={{ textAlign: 'center' }}>
              <div className="text-gradient" style={{ fontSize: 30, fontWeight: 800, marginBottom: 4 }}>{s.value}</div>
              <div style={{ fontSize: 13, color: 'var(--ink-muted)' }}>{s.label}</div>
            </div>
          ))}
        </div>

        {/* ─── Value cards ──────────────────────────────────────── */}
        <div style={{ fontFamily: 'var(--mono)', fontSize: 12, letterSpacing: '0.14em', color: 'var(--circuit-2)', marginBottom: 10 }}>
          WHY AFRIPLAN
        </div>
        <h2 style={{ fontSize: 'var(--text-xl)', marginBottom: 'var(--space-lg)' }}>Innovating the future of tender-ready estimating.</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 'var(--space-md)', marginBottom: 'var(--space-xl)' }}>
          {VALUE_CARDS.map((c) => (
            <ValueCard key={c.title} icon={c.icon} title={c.title} body={c.body} />
          ))}
        </div>

        {/* ─── How it works ─────────────────────────────────────── */}
        <div style={{ fontFamily: 'var(--mono)', fontSize: 12, letterSpacing: '0.14em', color: 'var(--circuit-2)', marginBottom: 8 }}>
          HOW IT WORKS
        </div>
        <h2 style={{ fontSize: 'var(--text-xl)', marginBottom: 'var(--space-lg)' }}>Four steps from drawing to tender.</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--space-md)', marginBottom: 'var(--space-xl)' }}>
          {STEPS.map((s) => (
            <StepStrip key={s.n} n={s.n} title={s.title} body={s.body} />
          ))}
        </div>
      </div>

      {/* ─── Trust strip (real photo, full-bleed) ───────────────── */}
      <div style={{ position: 'relative', height: 280, marginTop: 'var(--space-lg)' }}>
        <img src={trustImage} alt="Electrical site team" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }} />
        <div style={{
          position: 'absolute', inset: 0,
          background: 'linear-gradient(180deg, var(--paper) 0%, rgba(10,14,26,0.55) 35%, rgba(10,14,26,0.55) 65%, var(--paper) 100%)',
        }} />
        <div style={{
          position: 'relative', height: '100%', display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: '0 20px',
        }}>
          <h2 style={{ fontSize: 'var(--text-lg)', marginBottom: 8, color: '#fff' }}>Built for South African electrical contractors.</h2>
          <p style={{ fontSize: 14, color: 'rgba(255,255,255,0.75)', margin: 0, maxWidth: 460 }}>
            From site teams to tender desks — real drawings, real SANS compliance, real numbers.
          </p>
        </div>
      </div>

      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 clamp(20px, 5vw, 64px)' }}>
        <div style={{
          textAlign: 'center', padding: 'var(--space-lg) 0', fontFamily: 'var(--mono)',
          fontSize: 11, letterSpacing: '0.1em', color: 'var(--ink-muted)',
        }}>
          AFRIPLAN ELECTRICAL · DUAL-PIPELINE · SANS 10142-1:2017
        </div>
      </div>
    </div>
  );
}

function glowOrb(top, left, color) {
  return {
    position: 'absolute', top, left, width: 500, height: 500, borderRadius: '50%',
    background: color, filter: 'blur(100px)', pointerEvents: 'none', zIndex: 0,
  };
}
