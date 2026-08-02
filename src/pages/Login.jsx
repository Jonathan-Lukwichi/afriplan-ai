import loginImage from '../assets/images/login-panel-electrician.jpg';
import { Zap } from 'lucide-react';

/* Demo login only — per project decision, this is intentionally NOT real
   authentication. No backend call, no password check, no session token.
   Prefilled credentials; a click signs you in. See CLAUDE.md for what
   upgrading to real per-user accounts would require.
   Light editorial refresh: full-bleed photo panel with a serif pull quote,
   form side on paper. No "Forgot password?" or "Continue with Google" —
   both would be non-functional (this login is demo-only by design), and a
   fake OAuth button would misrepresent what actually happens on click. */
export default function Login({ onNavigate, onSignIn }) {
  return (
    <div className="login-grid" style={{ minHeight: '100vh', display: 'grid', gridTemplateColumns: '1fr', background: 'var(--paper)' }}>
      {/* Photo side — hidden on narrow viewports */}
      <div className="login-photo-side" style={{ position: 'relative', display: 'none', minHeight: 480 }}>
        <img src={loginImage} alt="Electrician working on a distribution board" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }} />
        <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(180deg, rgba(16,26,51,0.10) 0%, rgba(16,26,51,0.78) 100%)' }} />
        <div style={{ position: 'absolute', left: 64, right: 64, bottom: 64, display: 'flex', flexDirection: 'column', gap: 16 }}>
          <h2 style={{ fontSize: 42, color: '#FFFFFF', lineHeight: 1.15 }}>
            A day of take-off,<br /><em>done before lunch.</em>
          </h2>
          <p style={{ fontSize: 15, lineHeight: 1.7, color: 'rgba(255,255,255,0.82)', maxWidth: 400, margin: 0 }}>
            Upload the drawings, review the quantities, send the quotation.
          </p>
        </div>
      </div>

      {/* Form side */}
      <div style={{
        display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 34,
        padding: 'clamp(40px, 8vw, 80px) clamp(24px, 8vw, 104px)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 30, height: 30, borderRadius: 8, background: 'var(--blueprint)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Zap size={17} color="#fff" strokeWidth={2.5} />
          </div>
          <span style={{ fontSize: 21, fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--ink)' }}>
            Afri<span style={{ color: 'var(--blueprint)' }}>Plan</span> Electrical
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <h1 style={{ fontSize: 46 }}>Welcome <em>back</em></h1>
          <p style={{ fontSize: 15, color: 'var(--ink-2)', margin: 0 }}>
            Demo credentials are pre-filled — just click Sign in.
          </p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 18, maxWidth: 460 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
            <label htmlFor="afp-email" style={labelStyle}>Email</label>
            <input id="afp-email" defaultValue="demo@afriplan.local" style={inputStyle} />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
            <label htmlFor="afp-password" style={labelStyle}>Password</label>
            <input id="afp-password" type="password" defaultValue="afriplan-demo" style={inputStyle} />
          </div>

          <button onClick={onSignIn} className="btn-gradient" style={{ width: '100%', fontSize: 16, minHeight: 54 }}>
            Sign in
          </button>
        </div>

        <div style={{ textAlign: 'center' }}>
          <span style={{ fontSize: 13, color: 'var(--blueprint)', cursor: 'pointer' }} onClick={() => onNavigate('landing')}>← Back to home</span>
        </div>
      </div>
    </div>
  );
}

const labelStyle = { fontSize: 13, fontWeight: 500, color: 'var(--ink-2)' };

const inputStyle = {
  width: '100%', height: 52, padding: '0 16px', background: '#FFFFFF',
  border: '1px solid var(--hairline-2)', borderRadius: 10,
  fontSize: 15, color: 'var(--ink)',
};
