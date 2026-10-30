import { Zap } from 'lucide-react';

/* Public-page top nav. White sticky bar: wordmark, in-page section links
   (buttons that scroll, so the hash router is never touched), Sign in and
   the one primary action. No utility strip, no rating or market claims —
   only what the product does today. Link styles live in landing.css. */
const SECTIONS = [
  { id: 'how', label: 'How it works' },
  { id: 'evidence', label: 'Where numbers come from' },
  { id: 'savings', label: 'Time saved' },
  { id: 'faq', label: 'Questions' },
];

export function scrollToSection(id) {
  const el = document.getElementById(id);
  if (!el) return;
  const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  el.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
}

export default function Navbar({ onNavigate }) {
  return (
    <header style={{
      position: 'sticky', top: 0, zIndex: 20, background: 'rgba(255,255,255,0.92)',
      backdropFilter: 'saturate(1.4) blur(10px)', WebkitBackdropFilter: 'saturate(1.4) blur(10px)',
      borderBottom: '1px solid var(--hairline)',
    }}>
      <div style={{
        maxWidth: 1240, margin: '0 auto', display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', gap: 20, padding: '12px clamp(16px, 4vw, 32px)',
      }}>
        <button
          type="button"
          onClick={() => window.scrollTo({ top: 0 })}
          aria-label="AfriPlan Electrical, back to top"
          style={{ display: 'flex', alignItems: 'center', gap: 10, background: 'none', border: 0, padding: 0, cursor: 'pointer', minHeight: 32 }}
        >
          <span style={{
            width: 30, height: 30, borderRadius: 7, background: 'var(--blueprint)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          }}>
            <Zap size={17} color="#fff" strokeWidth={2.5} />
          </span>
          <span style={{ fontFamily: 'var(--display)', fontSize: 21, fontWeight: 700, letterSpacing: '-0.01em', color: 'var(--ink)', whiteSpace: 'nowrap' }}>
            AfriPlan <span className="lp-brand-sub" style={{ fontWeight: 500, color: 'var(--ink-2)' }}>Electrical</span>
          </span>
        </button>

        <nav className="navbar-link-wide lp-nav-sections" aria-label="Page sections" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          {SECTIONS.map((s) => (
            <button key={s.id} type="button" onClick={() => scrollToSection(s.id)} className="lp-navlink">
              {s.label}
            </button>
          ))}
        </nav>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <button type="button" onClick={() => onNavigate('login')} className="navbar-link-wide lp-navlink">
            Sign in
          </button>
          <button type="button" onClick={() => onNavigate('login')} className="btn-gradient" style={{ minHeight: 40, padding: '0 18px', fontSize: 14 }}>
            Start a BoQ
          </button>
        </div>
      </div>
    </header>
  );
}

