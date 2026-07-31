import { useState } from 'react';
import Landing from './pages/Landing';
import Login from './pages/Login';

// Demo login only (per project decision) — no backend call, no real session,
// just a client-side flag. See CLAUDE.md for why, and what upgrading to real
// auth would require.
const AUTH_KEY = 'afriplan_demo_authed';

const PAGES = {
  // Populated as each build phase lands:
  // welcome: Welcome, upload: Upload, extraction: Extraction, boq: Boq, pricing: Pricing,
};

function readHash() {
  const h = typeof window !== 'undefined' ? window.location.hash.slice(1) : '';
  return h && (PAGES[h] || h === 'landing' || h === 'login') ? h : 'landing';
}

export default function App() {
  const [page, setPageState] = useState(readHash);
  const setPage = (p) => {
    setPageState(p);
    try { window.location.hash = p; } catch {}
  };

  const isAuthed = () => {
    try { return localStorage.getItem(AUTH_KEY) === '1'; } catch { return false; }
  };
  const signIn = () => {
    try { localStorage.setItem(AUTH_KEY, '1'); } catch {}
    setPage('welcome');
  };

  if (page === 'landing') return <Landing onNavigate={setPage} />;
  if (page === 'login') return <Login onNavigate={setPage} onSignIn={signIn} />;

  if (!isAuthed()) return <Login onNavigate={setPage} onSignIn={signIn} />;

  const PageComponent = PAGES[page];
  if (!PageComponent) {
    // Wizard pages land in later build phases — placeholder keeps the app
    // runnable and the auth gate demonstrably working in the meantime.
    return (
      <div style={{ padding: 40, fontFamily: 'var(--sans)' }}>
        <h1>Signed in</h1>
        <p>The wizard (Welcome → Upload → Extraction → BOQ → Pricing) lands in later build phases.</p>
      </div>
    );
  }
  return <PageComponent onNavigate={setPage} />;
}
