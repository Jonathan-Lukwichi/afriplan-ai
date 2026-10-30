import { Check, FileText, FileSpreadsheet, Ruler, Hash, ScrollText, Eye, CircleHelp } from 'lucide-react';
import Navbar, { scrollToSection } from '../components/ui/Navbar';
import HeroTakeoff from '../components/landing/HeroTakeoff';
import SavingsCalculator from '../components/landing/SavingsCalculator';
import '../styles/landing.css';

import symCircuitSchedule from '../assets/images/symbols/glyph-circuit-schedule.png';
import symDistributionBoard from '../assets/images/symbols/glyph-distribution-board.png';
import symCable from '../assets/images/symbols/glyph-cable.png';
import symLuminaire from '../assets/images/symbols/glyph-luminaire.png';
import symSocket from '../assets/images/symbols/glyph-socket.png';
import symEarth from '../assets/images/symbols/glyph-earth.png';
import symContainment from '../assets/images/symbols/glyph-containment.png';
import symSolar from '../assets/images/symbols/glyph-solar.png';

/* Public marketing page, 2026-10-29 rebuild. Section order modelled on the
   BuildVision AI landing page (local screenshots in design-reference/,
   gitignored), but every claim is AfriPlan's own and true today: SANS
   10142-1:2017, South Africa, rand, PDF + DWG/DXF, evidence on every line
   (ADR-0008). No logo wall, ratings or testimonials — we have none to show. */

const HERO_FACTS = ['PDF, DWG and DXF drawing sets', 'Checked against SANS 10142-1:2017', 'Excel and PDF tender bill, in rand'];

const STEPS = [
  {
    title: 'Upload the drawing set',
    body: 'PDFs, DWG or DXF files, one sheet or the whole set: layouts, single-line diagrams, the site plan.',
    visual: 'files',
  },
  {
    title: 'Two readers take it off',
    body: 'The CAD reader measures the geometry. The drawing reader reads each PDF page. Their findings merge into one bill.',
    visual: 'readers',
  },
  {
    title: 'Check what is missing',
    body: 'Anything the drawings do not show is listed as a gap, never quietly guessed: a feeder with no size, a run with no length.',
    visual: 'gaps',
  },
  {
    title: 'Export the tender bill',
    body: 'Priced from your own rates and markup, set out by section with subtotals. Excel and PDF, ready to attach.',
    visual: 'export',
  },
];

const EVIDENCE = [
  { icon: Ruler, name: 'Measured', body: 'Taken off CAD geometry or a vector site plan, to scale.', eg: '186 m of 2.5 mm² wire' },
  { icon: Hash, name: 'Counted', body: 'Symbols matched to the legend and counted, sheet by sheet.', eg: '17 LED panels on WD-01' },
  { icon: ScrollText, name: 'Written', body: 'Read from a schedule, a single-line diagram or a drawing note.', eg: 'DB-1, 24-way, from the DB schedule' },
  { icon: Eye, name: 'Seen', body: 'Recognised on the page, but not something that can be counted exactly.', eg: 'Cable tray shown on the riser' },
  { icon: CircleHelp, name: 'Assumed', body: 'Not on the drawings. Priced from a stated assumption and listed as a gap.', eg: 'Surge protection, Type 2' },
];

const READS = [
  { img: symCircuitSchedule, label: 'Circuit schedules' },
  { img: symDistributionBoard, label: 'Distribution boards' },
  { img: symCable, label: 'Cable runs and lengths' },
  { img: symLuminaire, label: 'Luminaires' },
  { img: symSocket, label: 'Socket outlets' },
  { img: symEarth, label: 'Earthing and bonding' },
  { img: symContainment, label: 'Containment' },
  { img: symSolar, label: 'Solar and backup' },
];

const COMPARE = [
  { what: 'Counting symbols', manual: 'By hand, with a highlighter on a printed sheet', afp: 'Matched to the legend and counted on every sheet' },
  { what: 'Cable and conduit lengths', manual: 'Scale rule, or an estimate per point', afp: 'Measured on the CAD geometry or vector site plan' },
  { what: 'Where a number came from', manual: 'In the estimator’s notes, if anywhere', afp: 'Shown on every line: measured, counted, written, seen or assumed' },
  { what: 'Information the drawings lack', manual: 'Found on site, after the tender is won', afp: 'Listed in a gap report before you price' },
  { what: 'The tender document', manual: 'Retyped into a spreadsheet', afp: 'Excel and PDF bill, by section, with subtotals' },
];

const FAQ = [
  {
    q: 'How accurate is the first draft?',
    a: 'Treat it as a first draft you check, not a finished bill. Every line shows its evidence, so you know where to look first, and every assumed line is in the gap report. AfriPlan is tested against real, human-priced South African projects.',
  },
  {
    q: 'Which files can I upload?',
    a: 'PDF drawing sets, DWG and DXF. CAD files give measured lengths; PDF pages are read one by one. Upload both and the two readers’ findings are combined into one bill.',
  },
  {
    q: 'Which standard does it check against?',
    a: 'SANS 10142-1:2017: circuit limits, earth leakage protection and spare ways on distribution boards. Each bill is checked automatically.',
  },
  {
    q: 'Whose rates are used?',
    a: 'Yours. Keep your own rate library and markup default; every line is priced from it in rand, and you can change any rate before you export.',
  },
  {
    q: 'What do I get at the end?',
    a: 'A Bill of Quantities in Excel and PDF, set out by section with subtotals, plus the gap report of everything that was assumed.',
  },
];

function StepVisual({ kind }) {
  if (kind === 'files') {
    return (
      <ul className="lp-step-vis lp-files">
        {['WD-01 Lighting.pdf', 'WD-02 Power.dwg', 'SLD-01 Main board.pdf', 'Site plan.dxf'].map((f) => (
          <li key={f}><FileText size={14} aria-hidden="true" /> {f}</li>
        ))}
      </ul>
    );
  }
  if (kind === 'readers') {
    return (
      <div className="lp-step-vis lp-readers">
        <div><span>CAD reader</span><span className="lp-bar"><span style={{ width: '100%' }} /></span><span className="num">4 of 4 sheets</span></div>
        <div><span>Drawing reader</span><span className="lp-bar"><span style={{ width: '75%' }} /></span><span className="num">9 of 12 pages</span></div>
      </div>
    );
  }
  if (kind === 'gaps') {
    return (
      <ul className="lp-step-vis lp-gaps">
        <li><span className="lp-chip lp-chip-assumed">gap</span> Feeder DB-1 to DB-2: cable size not shown</li>
        <li><span className="lp-chip lp-chip-assumed">gap</span> Site lighting: trench length not dimensioned</li>
      </ul>
    );
  }
  return (
    <div className="lp-step-vis lp-exports">
      <span><FileSpreadsheet size={16} aria-hidden="true" /> BoQ.xlsx</span>
      <span><FileText size={16} aria-hidden="true" /> BoQ.pdf</span>
    </div>
  );
}

export default function Landing({ onNavigate }) {
  const start = () => onNavigate('login');

  return (
    <div className="lp">
      <Navbar onNavigate={onNavigate} />

      <main>
        {/* ─── Hero ─────────────────────────────────────────────── */}
        <section className="lp-hero lp-wrap" aria-labelledby="lp-hero-title">
          <div className="lp-hero-copy">
            <h1 id="lp-hero-title">Hand it the drawings. Get back a Bill of Quantities you can tender with.</h1>
            <div className="lp-hero-side">
              <p className="lp-lead">
                AfriPlan counts the symbols, measures the cable runs and prices each line from your own
                rates, in rand. Every quantity shows where it came from, so you check the bill instead
                of building it.
              </p>
              <div className="lp-actions">
                <button type="button" className="btn-gradient" onClick={start}>Start a BoQ</button>
                <button type="button" className="btn-ghost" onClick={() => scrollToSection('how')}>See how a bill is built</button>
              </div>
              <ul className="lp-facts">
                {HERO_FACTS.map((f) => (
                  <li key={f}><Check size={15} strokeWidth={2.5} aria-hidden="true" /> {f}</li>
                ))}
              </ul>
            </div>
          </div>
          <HeroTakeoff />
        </section>

        {/* ─── What it reads ────────────────────────────────────── */}
        <section className="lp-reads" aria-labelledby="lp-reads-title">
          <div className="lp-wrap">
            <h2 id="lp-reads-title" className="lp-h-small">What it picks up on an electrical drawing</h2>
            <ul className="lp-reads-list">
              {READS.map((r) => (
                <li key={r.label}>
                  <img src={r.img} alt="" />
                  <span>{r.label}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* ─── How it works (a real sequence, so it is numbered) ── */}
        <section id="how" className="lp-section lp-wrap" aria-labelledby="lp-how-title">
          <div className="lp-section-head">
            <h2 id="lp-how-title">From drawing set to tender bill, in one sitting</h2>
            <p>No new way of working. Upload what the consultant sent, check what AfriPlan found, export the bill.</p>
          </div>
          <ol className="lp-steps">
            {STEPS.map((s, i) => (
              <li key={s.title} className="lp-step">
                <span className="lp-step-n num" aria-hidden="true">{i + 1}</span>
                <h3>{s.title}</h3>
                <p>{s.body}</p>
                <StepVisual kind={s.visual} />
              </li>
            ))}
          </ol>
        </section>

        {/* ─── Evidence ladder ──────────────────────────────────── */}
        <section id="evidence" className="lp-section lp-evidence" aria-labelledby="lp-ev-title">
          <div className="lp-wrap lp-evidence-grid">
            <div className="lp-section-head">
              <h2 id="lp-ev-title">Every quantity says where it came from</h2>
              <p>
                A bill you can defend at tender. Each line carries one of five kinds of evidence, strongest
                first. When the two readers disagree, the stronger evidence wins.
              </p>
            </div>
            <ol className="lp-ladder">
              {EVIDENCE.map((e, i) => (
                <li key={e.name} className={`lp-rung lp-rung-${e.name.toLowerCase()}`}>
                  <span className="lp-rung-meter" aria-hidden="true">
                    {EVIDENCE.map((_, j) => <span key={j} className={j < EVIDENCE.length - i ? 'on' : ''} />)}
                  </span>
                  <e.icon size={20} aria-hidden="true" className="lp-rung-icon" />
                  <div>
                    <h3>{e.name}</h3>
                    <p>{e.body}</p>
                  </div>
                  <span className="lp-rung-eg">{e.eg}</span>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* ─── Savings calculator (the cyanotype band) ──────────── */}
        <section id="savings" className="lp-cyan" aria-labelledby="lp-calc-title">
          <div className="lp-wrap lp-cyan-inner">
            <div className="lp-section-head lp-on-dark">
              <h2 id="lp-calc-title">What take-off costs you now</h2>
              <p>Four numbers from your own office. Move the sliders and see the time a first draft gives back.</p>
            </div>
            <SavingsCalculator />
          </div>
        </section>

        {/* ─── Side by side ─────────────────────────────────────── */}
        <section className="lp-section lp-wrap" aria-labelledby="lp-cmp-title">
          <div className="lp-section-head">
            <h2 id="lp-cmp-title">Manual take-off and AfriPlan, side by side</h2>
          </div>
          <div className="lp-cmp" role="table" aria-label="Manual take-off compared with AfriPlan">
            <div className="lp-cmp-row lp-cmp-headrow" role="row">
              <span role="columnheader"><span className="lp-visually-hidden">Task</span></span>
              <span role="columnheader">By hand</span>
              <span role="columnheader">With AfriPlan</span>
            </div>
            {COMPARE.map((c) => (
              <div key={c.what} className="lp-cmp-row" role="row">
                <span role="rowheader" className="lp-cmp-what">{c.what}</span>
                <span role="cell" className="lp-cmp-manual"><span className="lp-cmp-label" aria-hidden="true">By hand</span>{c.manual}</span>
                <span role="cell" className="lp-cmp-afp"><span className="lp-cmp-label" aria-hidden="true">With AfriPlan</span>{c.afp}</span>
              </div>
            ))}
          </div>
        </section>

        {/* ─── FAQ ──────────────────────────────────────────────── */}
        <section id="faq" className="lp-section lp-wrap lp-faq" aria-labelledby="lp-faq-title">
          <div className="lp-section-head">
            <h2 id="lp-faq-title">Questions contractors ask first</h2>
          </div>
          <div className="lp-faq-list">
            {FAQ.map((f) => (
              <details key={f.q}>
                <summary>{f.q}</summary>
                <p>{f.a}</p>
              </details>
            ))}
          </div>
        </section>

        {/* ─── Closing call to action ───────────────────────────── */}
        <section className="lp-final lp-wrap" aria-labelledby="lp-final-title">
          <h2 id="lp-final-title">Price your next tender from the drawings.</h2>
          <p>Upload a set and see the first draft of the bill, with every gap listed.</p>
          <div className="lp-actions">
            <button type="button" className="btn-gradient" onClick={start}>Start a BoQ</button>
            <button type="button" className="btn-ghost" onClick={start}>Sign in</button>
          </div>
        </section>
      </main>

      <footer className="lp-footer">
        <div className="lp-wrap lp-footer-inner">
          <div className="lp-footer-brand">
            <strong>AfriPlan Electrical</strong>
            <p>Bills of Quantities from South African electrical drawings: counted, measured and priced in rand.</p>
          </div>
          <nav aria-label="Footer">
            <h2 className="lp-footer-h">Product</h2>
            <ul>
              <li><button type="button" onClick={() => scrollToSection('how')}>How it works</button></li>
              <li><button type="button" onClick={() => scrollToSection('evidence')}>Where numbers come from</button></li>
              <li><button type="button" onClick={() => scrollToSection('savings')}>Time saved</button></li>
              <li><button type="button" onClick={() => scrollToSection('faq')}>Questions</button></li>
            </ul>
          </nav>
          <nav aria-label="Account">
            <h2 className="lp-footer-h">Account</h2>
            <ul>
              <li><button type="button" onClick={start}>Sign in</button></li>
              <li><button type="button" onClick={start}>Start a BoQ</button></li>
            </ul>
          </nav>
        </div>
        <div className="lp-wrap lp-footer-base">
          <span>© 2026 AfriPlan Electrical, by JLWanalytics.</span>
          <span>Drawings in, priced Bill of Quantities out.</span>
        </div>
      </footer>
    </div>
  );
}
