import Navbar from '../components/ui/Navbar';
import heroSwitchgear from '../assets/images/hero-switchgear.jpg';
import solarInstall from '../assets/images/solar-install.jpg';
import loginPanel from '../assets/images/login-panel-electrician.jpg';
import trustImage from '../assets/images/trust-strip-site-team.jpg';
import rebarSite from '../assets/images/rebar-site.jpg';
import goldenHour from '../assets/images/header-banner-goldenhour.jpg';

import symCircuitSchedule from '../assets/images/symbols/glyph-circuit-schedule.png';
import symDistributionBoard from '../assets/images/symbols/glyph-distribution-board.png';
import symCable from '../assets/images/symbols/glyph-cable.png';
import symLuminaire from '../assets/images/symbols/glyph-luminaire.png';
import symSocket from '../assets/images/symbols/glyph-socket.png';
import symEarth from '../assets/images/symbols/glyph-earth.png';
import symContainment from '../assets/images/symbols/glyph-containment.png';
import symSolar from '../assets/images/symbols/glyph-solar.png';

/* Public marketing page — light editorial refresh (structure/layout from
   the Lovable "afriplan-refresh" bundle), with copy corrected to match what
   the product actually does today: SANS 10142-1:2017, South Africa, ZAR.
   The bundle's original copy claimed multi-currency support across 14
   African markets and a fabricated "we timed eleven engineers" study —
   neither is true of this backend, so both were rewritten rather than
   shipped as-is. */

const PANORAMA_TOP = [heroSwitchgear, solarInstall, loginPanel, trustImage, rebarSite, goldenHour];
const PANORAMA_BOTTOM = [trustImage, goldenHour, heroSwitchgear, rebarSite, solarInstall, loginPanel];

const HERO_POINTS = [
  'Reads DXF, DWG and PDF drawing sets',
  'Two engines cross-check every quantity',
  'Checked against SANS 10142-1:2017 automatically',
];

const STATS = [
  { value: 'R 0.00', label: 'DXF engine cost per run' },
  { value: '2', label: 'Independent extraction engines' },
  { value: '10142-1', label: 'SANS standard, checked automatically' },
  { value: '5-sheet', label: 'Tender-grade export document' },
];

const STEPS = [
  { n: '01', title: 'Upload the drawings', body: 'A DXF or DWG export, a PDF drawing set, or both together.' },
  { n: '02', title: 'Watch the take-off', body: 'Symbols counted, cable measured, legend resolved — live as it lands.' },
  { n: '03', title: 'Review the BoQ', body: 'Every line labelled extracted, inferred or assumed. Nothing hidden.' },
  { n: '04', title: 'Send the quotation', body: 'Your margin, your markup, your letterhead — Excel and PDF.' },
];

const READS = [
  { img: symCircuitSchedule, label: 'Circuit schedules' },
  { img: symDistributionBoard, label: 'Distribution boards' },
  { img: symCable, label: 'Cable runs & lengths' },
  { img: symLuminaire, label: 'Luminaires' },
  { img: symSocket, label: 'Socket outlets' },
  { img: symEarth, label: 'Earthing & bonding' },
  { img: symContainment, label: 'Containment' },
  { img: symSolar, label: 'Solar & backup' },
];

const NOTES = [
  {
    meta: 'PRODUCTIVITY',
    title: 'Where manual take-off actually loses you time',
    body: 'Counting symbols, measuring cable runs and retyping schedules into a spreadsheet is the least valuable part of the job — and the easiest to automate.',
  },
  {
    meta: 'ENGINES',
    title: 'When the DXF and the PDF disagree',
    body: 'A layer-naming inconsistency in the drawing is the most common cause of a cable-length variance between the two engines. How to read the comparison panel.',
  },
  {
    meta: 'COMPLIANCE',
    title: 'What SANS 10142-1:2017 actually checks',
    body: 'Circuit limits, ELCB requirements and spare-way margins — the specific rules AfriPlan validates every bill against, automatically.',
  },
];

export default function Landing({ onNavigate }) {
  return (
    <div style={{ background: 'var(--paper)', minHeight: '100vh', overflowX: 'hidden' }}>
      <Navbar onNavigate={onNavigate} />

      {/* ─── Hero ───────────────────────────────────────────────── */}
      <div style={{ maxWidth: 1440, margin: '0 auto' }}>
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: 'var(--space-lg)', alignItems: 'end',
          padding: 'clamp(48px, 8vw, 96px) clamp(20px, 6vw, 104px) 0',
        }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
            <span style={{ fontFamily: 'var(--mono)', fontSize: 12, letterSpacing: '0.16em', color: 'var(--circuit)' }}>
              DRAWING → BoQ → QUOTATION
            </span>
            <h1 style={{ fontSize: 'var(--text-2xl)' }}>
              <em style={{ display: 'block' }}>Drawings in.</em>
              Quotations out.
            </h1>
            <p style={{ fontSize: 'var(--text-lg)', lineHeight: 1.6, color: 'var(--ink-2)', maxWidth: 520, margin: 0, textWrap: 'pretty' }}>
              AfriPlan reads your electrical plan drawings, builds the Bill of Quantities
              line by line and prices it into a client-ready quotation — no manual
              take-off required.
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 14, paddingBottom: 8 }}>
            {HERO_POINTS.map((point) => (
              <div key={point} style={{ display: 'flex', alignItems: 'center', gap: 14, fontSize: 17 }}>
                <span style={tickStyle}>✓</span>
                <span style={{ color: 'var(--ink-2)' }}>{point}</span>
              </div>
            ))}
            <div style={{ display: 'flex', alignItems: 'center', gap: 22, flexWrap: 'wrap', paddingTop: 14 }}>
              <button onClick={() => onNavigate('login')} className="btn-gradient" style={{ fontSize: 16, minHeight: 54, padding: '0 34px' }}>
                Start your BoQ
              </button>
            </div>
          </div>
        </div>

        {/* Moving panorama */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18, overflow: 'hidden', padding: 'clamp(40px, 6vw, 64px) 0 clamp(48px, 7vw, 96px)' }}>
          <div className="afp-panorama-strip" style={{ display: 'flex', gap: 18, width: 'max-content', animation: 'afp-pan-left 52s linear infinite' }}>
            {[...PANORAMA_TOP, ...PANORAMA_TOP].map((src, i) => (
              <img key={`t${i}`} src={src} alt="" style={{ width: 420, height: 264, objectFit: 'cover', borderRadius: 10 }} />
            ))}
          </div>
          <div className="afp-panorama-strip" style={{ display: 'flex', gap: 18, width: 'max-content', animation: 'afp-pan-right 64s linear infinite' }}>
            {[...PANORAMA_BOTTOM, ...PANORAMA_BOTTOM].map((src, i) => (
              <img key={`b${i}`} src={src} alt="" style={{ width: 300, height: 180, objectFit: 'cover', borderRadius: 10 }} />
            ))}
          </div>
        </div>

        {/* ─── Stats band ─────────────────────────────────────────── */}
        <div style={{ padding: '0 clamp(20px, 6vw, 104px) clamp(56px, 8vw, 104px)' }}>
          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            borderTop: '1px solid var(--hairline)', borderBottom: '1px solid var(--hairline)',
          }}>
            {STATS.map((s) => (
              <div key={s.label} style={{ padding: '34px 28px', display: 'flex', flexDirection: 'column', gap: 8, borderRight: '1px solid var(--hairline)' }}>
                <span style={{ fontFamily: 'var(--serif)', fontSize: 38, fontWeight: 700, color: 'var(--ink)' }}>{s.value}</span>
                <span style={{ fontSize: 13, color: 'var(--ink-2)' }}>{s.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* ─── Where the hours go ─────────────────────────────────── */}
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 'clamp(40px, 6vw, 80px)',
          padding: '0 clamp(20px, 6vw, 104px) clamp(56px, 8vw, 110px)', alignItems: 'center',
        }}>
          <div style={{ position: 'relative', minHeight: 360 }}>
            <div style={{ position: 'absolute', inset: 0, background: 'var(--paper-edge)', borderRadius: '200px 200px 24px 200px' }} />
            <img src={rebarSite} alt="Electrical site work" style={{ position: 'relative', left: 40, top: 36, width: 'calc(100% - 80px)', height: 288, objectFit: 'cover', borderRadius: 12 }} />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
            <h2 style={{ fontSize: 'var(--text-xl)' }}>Where the <em>hours go</em></h2>
            <p style={{ fontSize: 16, lineHeight: 1.75, color: 'var(--ink-2)', maxWidth: 460, margin: 0, textWrap: 'pretty' }}>
              Counting symbols. Measuring cable runs. Retyping schedules into a spreadsheet.
              Chasing the rate you used last month. It is the least valuable part of an
              electrical engineer&rsquo;s week. AfriPlan does the counting, the measuring and
              the pricing — you review, adjust and send.
            </p>
            <div style={{ width: 64, height: 2, background: 'var(--blueprint)' }} />
          </div>
        </div>

        {/* ─── Four steps ─────────────────────────────────────────── */}
        <div style={{ padding: '0 clamp(20px, 6vw, 104px) clamp(56px, 8vw, 110px)', display: 'flex', flexDirection: 'column', gap: 'var(--space-lg)' }}>
          <h2 style={{ fontSize: 'var(--text-xl)' }}>Four steps, <em>one sitting</em></h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 28 }}>
            {STEPS.map((s, i) => (
              <div key={s.n} style={{
                display: 'flex', flexDirection: 'column', gap: 12, paddingTop: 20,
                borderTop: `2px solid ${i === 0 ? 'var(--blueprint)' : 'var(--hairline-2)'}`,
              }}>
                <span style={{ fontFamily: 'var(--mono)', fontSize: 12, color: i === 0 ? 'var(--blueprint)' : 'var(--ink-muted)' }}>{s.n}</span>
                <h3 style={{ fontSize: 19 }}>{s.title}</h3>
                <p style={{ fontSize: 14, lineHeight: 1.7, color: 'var(--ink-2)', margin: 0 }}>{s.body}</p>
              </div>
            ))}
          </div>
        </div>

        {/* ─── What it reads ──────────────────────────────────────── */}
        <div style={{ padding: '0 clamp(20px, 6vw, 104px) clamp(56px, 8vw, 110px)', display: 'flex', flexDirection: 'column', gap: 'var(--space-lg)' }}>
          <h2 style={{ fontSize: 'var(--text-xl)', textAlign: 'center' }}>What it <em>reads</em></h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '28px 24px' }}>
            {READS.map((r) => (
              <div key={r.label} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div style={{
                  height: 150, borderRadius: 10, background: 'var(--card-bg-2)',
                  border: '1px solid rgba(16,26,51,0.07)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <img src={r.img} alt={`${r.label} symbol`} style={{ height: 88, width: 'auto', objectFit: 'contain' }} />
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--hairline)', paddingBottom: 10 }}>
                  <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--blueprint)' }}>{r.label}</span>
                  <span style={{ color: 'var(--ink-muted)' }}>›</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ─── Built for South African electrical contractors ───────── */}
      <div style={{ background: 'var(--paper-2)' }}>
        <div style={{
          maxWidth: 1440, margin: '0 auto', padding: 'clamp(56px, 8vw, 104px) clamp(20px, 6vw, 104px)',
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 'clamp(40px, 6vw, 90px)', alignItems: 'center',
        }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
            <h2 style={{ fontSize: 'var(--text-xl)' }}>
              Built for South African<br />
              <em style={{ borderBottom: '2px solid var(--blueprint)', paddingBottom: 4 }}>electrical contractors</em>
            </h2>
            <p style={{ fontSize: 16, lineHeight: 1.75, color: 'var(--ink-2)', maxWidth: 440, margin: 0, textWrap: 'pretty' }}>
              From site teams to tender desks — real drawings, real SANS 10142-1:2017
              compliance, real numbers in rand. Keep your own rate library and markup
              defaults, and let the two engines cross-check every quantity before it
              goes into a client quotation.
            </p>
            <button onClick={() => onNavigate('login')} className="btn-ghost" style={{ alignSelf: 'flex-start' }}>
              About AfriPlan
            </button>
          </div>
          <div style={{ position: 'relative' }}>
            <div style={{ position: 'absolute', left: 16, top: 16, width: '100%', height: '100%', background: 'var(--blueprint)', borderRadius: 14 }} />
            <img src={trustImage} alt="Electrical site team" style={{ position: 'relative', width: '100%', height: 340, objectFit: 'cover', borderRadius: 14, display: 'block' }} />
          </div>
        </div>
      </div>

      {/* ─── Field notes ──────────────────────────────────────────── */}
      <div style={{ background: 'var(--paper-edge)' }}>
        <div style={{ maxWidth: 1440, margin: '0 auto', padding: 'clamp(48px, 7vw, 96px) clamp(20px, 6vw, 104px)', display: 'flex', flexDirection: 'column', gap: 'var(--space-lg)' }}>
          <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 20, flexWrap: 'wrap' }}>
            <h2 style={{ fontSize: 'var(--text-xl)', borderBottom: '2px solid var(--blueprint)', paddingBottom: 8 }}>Field <em>notes</em></h2>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 44 }}>
            {NOTES.map((n) => (
              <div key={n.title} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <span style={{ fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.1em', color: 'var(--ink-muted)' }}>{n.meta}</span>
                <h3 style={{ fontFamily: 'var(--serif)', fontSize: 20, fontWeight: 700, lineHeight: 1.3 }}>{n.title}</h3>
                <p style={{ fontSize: 14, lineHeight: 1.7, color: 'var(--ink-2)', margin: 0 }}>{n.body}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ─── Footer ───────────────────────────────────────────────── */}
      <div style={{ background: 'var(--paper-2)' }}>
        <div style={{
          maxWidth: 1440, margin: '0 auto', padding: 'clamp(48px, 7vw, 88px) clamp(20px, 6vw, 104px) 40px',
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 60,
        }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <h2 style={{ fontSize: 34 }}>Price your <em>next job</em></h2>
            <span style={{ fontFamily: 'var(--serif)', fontStyle: 'italic', fontSize: 20, color: 'var(--blueprint)', cursor: 'pointer' }} onClick={() => onNavigate('login')}>
              Get started
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <span style={footerHeading}>MENU</span>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 20px', fontSize: 14, color: 'var(--ink-2)' }}>
              <span>Product</span>
              <span>How it works</span>
              <span onClick={() => onNavigate('login')} style={{ cursor: 'pointer' }}>Sign in</span>
            </div>
          </div>
        </div>
        <div style={{
          maxWidth: 1440, margin: '0 auto', padding: '24px clamp(20px, 6vw, 104px) 40px',
          borderTop: '1px solid var(--hairline)', display: 'flex', justifyContent: 'space-between',
          gap: 16, flexWrap: 'wrap', fontSize: 12, color: 'var(--ink-muted)',
        }}>
          <span>AfriPlan Electrical.</span>
          <span style={{ fontFamily: 'var(--mono)' }}>DRAWING · BoQ · QUOTATION</span>
        </div>
      </div>
    </div>
  );
}

const tickStyle = {
  width: 22, height: 22, borderRadius: '50%', background: 'var(--ink)', color: '#fff',
  fontSize: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
};

const footerHeading = {
  fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.14em', color: 'var(--ink-muted)',
};
