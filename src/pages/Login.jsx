/* Demo login only — per project decision, this is intentionally NOT real
   authentication. No backend call, no password check, no session token.
   Matches the exact pattern used elsewhere (prefilled credentials, a click
   signs you in). See CLAUDE.md for what upgrading to real per-user accounts
   would require if that's ever revisited — contractor-profile persistence
   (Phase 11) is currently a single shared demo profile, not per-user, as a
   direct consequence of this choice. */
export default function Login({ onNavigate, onSignIn }) {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--paper)' }}>
      <div style={{ width: '100%', maxWidth: 380, padding: 'var(--space-lg)', background: 'var(--paper-2)', border: '1px solid var(--hairline-2)', borderRadius: 'var(--radius-md)' }}>
        <div style={{ fontFamily: 'var(--mono)', fontSize: 12, letterSpacing: '0.12em', color: 'var(--circuit-2)', marginBottom: 8 }}>
          AFRIPLAN ELECTRICAL
        </div>
        <h2 style={{ fontSize: 22, marginBottom: 6 }}>Sign in</h2>
        <p style={{ fontSize: 14, color: 'var(--ink-muted)', margin: '0 0 24px' }}>Demo credentials are pre-filled — just click Sign in.</p>

        <label style={{ fontSize: 13, color: 'var(--ink-muted)', display: 'block', marginBottom: 4 }}>Email</label>
        <input
          defaultValue="demo@afriplan.local"
          style={{ width: '100%', padding: 10, marginBottom: 14, border: '1px solid var(--hairline-2)', borderRadius: 'var(--radius-sm)', fontSize: 14 }}
        />
        <label style={{ fontSize: 13, color: 'var(--ink-muted)', display: 'block', marginBottom: 4 }}>Password</label>
        <input
          type="password"
          defaultValue="afriplan-demo"
          style={{ width: '100%', padding: 10, marginBottom: 22, border: '1px solid var(--hairline-2)', borderRadius: 'var(--radius-sm)', fontSize: 14 }}
        />

        <button
          onClick={onSignIn}
          style={{ width: '100%', padding: 12, background: 'var(--blueprint)', color: 'white', border: 'none', borderRadius: 'var(--radius-sm)', fontSize: 15, fontWeight: 600, cursor: 'pointer', minHeight: 44 }}
        >
          Sign in
        </button>

        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <span style={{ fontSize: 13, color: 'var(--blueprint)', cursor: 'pointer' }} onClick={() => onNavigate('landing')}>← Back to home</span>
        </div>
      </div>
    </div>
  );
}
