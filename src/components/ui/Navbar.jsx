import { Zap } from 'lucide-react';

/* Public-page top nav — light editorial refresh. A thin utility bar states
   what the product actually does (no fabricated star rating or market-count
   claim — kept to what's true today: SANS 10142-1, South Africa) above a
   white sticky nav with a pill CTA. */
export default function Navbar({ onNavigate }) {
  return (
    <header style={{ position: 'sticky', top: 0, zIndex: 20 }}>
      <div style={{
        background: '#16203C', display: 'flex', alignItems: 'center', justifyContent: 'center',
        gap: 16, padding: '9px clamp(20px, 6vw, 40px)', flexWrap: 'wrap',
      }}>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.1em', color: '#C7CEE2' }}>
          DUAL-ENGINE TAKE-OFF · SANS 10142-1:2017 CHECKED · SOUTH AFRICA
        </span>
      </div>

      <div style={{
        background: '#FFFFFF', borderBottom: '1px solid var(--hairline)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        gap: 20, padding: '15px clamp(20px, 6vw, 40px)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 30, height: 30, borderRadius: 8, background: 'var(--blueprint)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          }}>
            <Zap size={17} color="#fff" strokeWidth={2.5} />
          </div>
          <span style={{ fontSize: 21, fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--ink)' }}>
            Afri<span style={{ color: 'var(--blueprint)' }}>Plan</span> Electrical
          </span>
        </div>

        <nav className="navbar-link-wide" style={{ display: 'flex', alignItems: 'center', gap: 'clamp(16px, 2.5vw, 34px)' }}>
          <a href="#landing" style={navLink}>Product</a>
          <a href="#landing" style={navLink}>How it works</a>
        </nav>

        <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
          <span
            onClick={() => onNavigate('login')}
            style={{ fontSize: 15, fontWeight: 600, color: 'var(--ink)', cursor: 'pointer' }}
          >
            Sign in
          </span>
          <button onClick={() => onNavigate('login')} className="btn-gradient" style={{ minHeight: 46, padding: '0 24px' }}>
            Start your BoQ →
          </button>
        </div>
      </div>
    </header>
  );
}

const navLink = {
  color: 'var(--ink)', textDecoration: 'none', fontSize: 15, fontWeight: 500,
};
