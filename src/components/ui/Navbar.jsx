import { Zap } from 'lucide-react';

/* Public-page top nav (Landing only — Login keeps a simpler centered-card
   treatment with no navbar, matching the Robotiko/Dashdark reference's own
   pattern of a bare auth screen). */
export default function Navbar({ onNavigate }) {
  return (
    <header style={{
      position: 'sticky', top: 0, zIndex: 20,
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '18px clamp(20px, 5vw, 64px)',
      background: 'rgba(10, 14, 26, 0.72)',
      backdropFilter: 'blur(14px)', WebkitBackdropFilter: 'blur(14px)',
      borderBottom: '1px solid var(--hairline)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{
          width: 34, height: 34, borderRadius: 9, background: 'var(--gradient-primary)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
        }}>
          <Zap size={18} color="#05070F" strokeWidth={2.5} />
        </div>
        <span style={{ fontWeight: 800, fontSize: 16, letterSpacing: '-0.01em' }}>AfriPlan</span>
      </div>

      <nav style={{ display: 'flex', alignItems: 'center', gap: 'clamp(10px, 2vw, 20px)' }}>
        <a href="#landing" style={navLink} className="navbar-link-wide">Product</a>
        <a href="#landing" style={navLink} className="navbar-link-wide">How it works</a>
        <button onClick={() => onNavigate('login')} className="btn-ghost" style={{ padding: '9px 18px', minHeight: 38 }}>
          Sign in
        </button>
        <button onClick={() => onNavigate('login')} className="btn-gradient" style={{ padding: '9px 20px', minHeight: 38 }}>
          Start your BoQ
        </button>
      </nav>
    </header>
  );
}

const navLink = {
  color: 'var(--ink-2)', textDecoration: 'none', fontSize: 14, fontWeight: 600,
};
