import { Zap } from 'lucide-react';
import loginImage from '../assets/images/login-panel-electrician.jpg';

/* Demo login only — per project decision, this is intentionally NOT real
   authentication. No backend call, no password check, no session token.
   Matches the exact pattern used elsewhere (prefilled credentials, a click
   signs you in). See CLAUDE.md for what upgrading to real per-user accounts
   would require if that's ever revisited — contractor-profile persistence
   (Phase 11) is currently a single shared demo profile, not per-user, as a
   direct consequence of this choice. */
export default function Login({ onNavigate, onSignIn }) {
  return (
    <div className="login-grid" style={{ minHeight: '100vh', display: 'grid', gridTemplateColumns: '1fr', background: 'var(--paper)', overflow: 'hidden' }}>
      {/* Photo side — hidden on narrow viewports */}
      <div className="login-photo-side" style={{ position: 'relative', display: 'none' }}>
        <img src={loginImage} alt="Electrician working on a distribution board" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }} />
        <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(115deg, rgba(10,14,26,0.85), rgba(10,14,26,0.35) 60%, transparent)' }} />
        <div style={{ position: 'absolute', bottom: 48, left: 48, right: 48 }}>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 12, letterSpacing: '0.14em', color: 'var(--circuit-2)', marginBottom: 10 }}>
            AFRIPLAN ELECTRICAL
          </div>
          <h2 style={{ fontSize: 26, color: '#fff', maxWidth: 380, lineHeight: 1.25 }}>
            Every drawing becomes a tender-ready bill, automatically.
          </h2>
        </div>
      </div>

      {/* Form side */}
      <div style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 'var(--space-md)' }}>
        <div style={glowOrb('10%', '20%')} />
        <div className="glass-card" style={{ position: 'relative', width: '100%', maxWidth: 380, padding: 'var(--space-lg)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 22 }}>
            <div style={{ width: 34, height: 34, borderRadius: 9, background: 'var(--gradient-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Zap size={18} color="#05070F" strokeWidth={2.5} />
            </div>
            <span style={{ fontFamily: 'var(--mono)', fontSize: 12, letterSpacing: '0.12em', color: 'var(--circuit-2)' }}>
              AFRIPLAN ELECTRICAL
            </span>
          </div>

          <h2 style={{ fontSize: 24, marginBottom: 6 }}>Sign in</h2>
          <p style={{ fontSize: 14, color: 'var(--ink-muted)', margin: '0 0 26px' }}>Demo credentials are pre-filled — just click Sign in.</p>

          <label style={{ fontSize: 13, color: 'var(--ink-muted)', display: 'block', marginBottom: 6 }}>Email</label>
          <input
            defaultValue="demo@afriplan.local"
            style={{
              width: '100%', padding: '12px 14px', marginBottom: 16, background: 'rgba(255,255,255,0.03)',
              border: '1px solid var(--hairline-2)', borderRadius: 'var(--radius-sm)', fontSize: 14, color: 'var(--ink)',
            }}
          />
          <label style={{ fontSize: 13, color: 'var(--ink-muted)', display: 'block', marginBottom: 6 }}>Password</label>
          <input
            type="password"
            defaultValue="afriplan-demo"
            style={{
              width: '100%', padding: '12px 14px', marginBottom: 24, background: 'rgba(255,255,255,0.03)',
              border: '1px solid var(--hairline-2)', borderRadius: 'var(--radius-sm)', fontSize: 14, color: 'var(--ink)',
            }}
          />

          <button onClick={onSignIn} className="btn-gradient" style={{ width: '100%', fontSize: 15 }}>
            Sign in
          </button>

          <div style={{ textAlign: 'center', marginTop: 18 }}>
            <span style={{ fontSize: 13, color: 'var(--blueprint-2)', cursor: 'pointer' }} onClick={() => onNavigate('landing')}>← Back to home</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function glowOrb(top, left) {
  return {
    position: 'absolute', top, left, width: 400, height: 400, borderRadius: '50%',
    background: 'var(--glow-blue)', filter: 'blur(90px)', pointerEvents: 'none', zIndex: 0,
  };
}
