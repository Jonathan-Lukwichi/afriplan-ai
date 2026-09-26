import { useState } from 'react';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Welcome from './pages/Welcome';
import Upload from './pages/Upload';
import Extraction from './pages/Extraction';
import Compare from './pages/Compare';
import Boq from './pages/Boq';
import Pricing from './pages/Pricing';
import Audit from './pages/Audit';
import AppShell from './components/ui/AppShell';

// Demo login only (per project decision) — no backend call, no real session,
// just a client-side flag. See CLAUDE.md for why, and what upgrading to real
// auth would require.
const AUTH_KEY = 'afriplan_demo_authed';

const PAGES = {
  welcome: Welcome,
  upload: Upload,
  extraction: Extraction,
  compare: Compare,
  boq: Boq,
  pricing: Pricing,
  audit: Audit,
};

function readHash() {
  const h = typeof window !== 'undefined' ? window.location.hash.slice(1) : '';
  return h && (PAGES[h] || h === 'landing' || h === 'login') ? h : 'landing';
}

export default function App() {
  const [page, setPageState] = useState(readHash);
  const [runId, setRunId] = useState(null);
  const [compareId, setCompareId] = useState(null);
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
  const signOut = () => {
    try { localStorage.removeItem(AUTH_KEY); } catch {}
    setPage('landing');
  };

  if (page === 'landing') return <Landing onNavigate={setPage} />;
  if (page === 'login') return <Login onNavigate={setPage} onSignIn={signIn} />;

  if (!isAuthed()) return <Login onNavigate={setPage} onSignIn={signIn} />;

  const PageComponent = PAGES[page];
  if (!PageComponent) {
    return (
      <div style={{ padding: 40, fontFamily: 'var(--sans)' }}>
        <h1>Signed in</h1>
        <p>Page not found.</p>
      </div>
    );
  }
  return (
    <AppShell activePage={page} onNavigate={setPage} onSignOut={signOut}>
      <PageComponent
        onNavigate={setPage}
        runId={runId}
        onRunCreated={setRunId}
        compareId={compareId}
        onCompareCreated={setCompareId}
      />
    </AppShell>
  );
}
