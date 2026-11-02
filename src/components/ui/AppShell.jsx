import { useEffect, useState } from 'react';
import {
  FileText, Home, Layers, LogOut, Menu, ShieldCheck, Upload as UploadIcon, Wallet, X, Zap,
} from 'lucide-react';

// Only pricing a job is a sequence, so only its steps are numbered.
const NAV_GROUPS = [
  { items: [{ page: 'welcome', label: 'Welcome', icon: Home }] },
  {
    title: 'Price a job',
    items: [
      { page: 'upload', label: 'Upload', step: 1, icon: UploadIcon },
      { page: 'extraction', label: 'Take-off', step: 2, icon: Layers },
      // No Compare entry: "Both, compare" on Upload opens that page with its result.
      { page: 'boq', label: 'BoQ', step: 3, icon: FileText },
      { page: 'pricing', label: 'Pricing', step: 4, icon: Wallet },
    ],
  },
  { title: 'Check a bill', items: [{ page: 'audit', label: 'Audit a BoQ', icon: ShieldCheck }] },
];

const PAGE_TITLES = {
  ...Object.fromEntries(NAV_GROUPS.flatMap((g) => g.items).map((i) => [i.page, i.label])),
  compare: 'Compare',
};

const STORAGE_KEY = 'afriplan.sidebarOpen';

/* Persistent authenticated-app layout — light editorial refresh.
   The sidebar is now collapsible on every viewport (☰ in the top bar), and
   the desktop preference persists. Below 820px the sidebar is hidden by the
   stylesheet and the same button opens it as an overlay drawer. */
export default function AppShell({ activePage, onNavigate, onSignOut, children }) {
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    if (typeof window === 'undefined') return true;
    return window.localStorage.getItem(STORAGE_KEY) !== 'false';
  });
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, String(sidebarOpen));
  }, [sidebarOpen]);

  const go = (page) => {
    onNavigate(page);
    setDrawerOpen(false);
  };

  const onToggle = () => {
    // Narrow viewports hide the docked sidebar entirely (see tokens.css), so
    // the same control opens the overlay drawer there instead.
    if (window.matchMedia('(max-width: 820px)').matches) setDrawerOpen(true);
    else setSidebarOpen((v) => !v);
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--paper)', display: 'flex' }}>
      {sidebarOpen && (
        <Sidebar activePage={activePage} onNavigate={go} onSignOut={onSignOut} className="app-sidebar" />
      )}

      {drawerOpen && (
        <>
          <div
            onClick={() => setDrawerOpen(false)}
            style={{ position: 'fixed', inset: 0, background: 'rgba(16,26,51,0.45)', zIndex: 40 }}
          />
          <div style={{ position: 'fixed', top: 0, left: 0, bottom: 0, zIndex: 50, width: 'var(--sidebar-width)' }}>
            <Sidebar activePage={activePage} onNavigate={go} onSignOut={onSignOut} onClose={() => setDrawerOpen(false)} showClose />
          </div>
        </>
      )}

      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
        <header className="app-topbar">
          <button
            type="button"
            className="app-topbar-menu"
            onClick={onToggle}
            aria-label={sidebarOpen ? 'Hide menu' : 'Show menu'}
            title={sidebarOpen ? 'Hide menu' : 'Show menu'}
          >
            <Menu size={17} aria-hidden="true" />
          </button>
          <span className="app-topbar-title">{PAGE_TITLES[activePage] || 'AfriPlan'}</span>
          <span className="app-topbar-note navbar-link-wide">Prices in rand, excl. VAT</span>
        </header>

        <div style={{ flex: 1, overflowY: 'auto' }}>
          {children}
        </div>
      </div>
    </div>
  );
}

function Sidebar({ activePage, onNavigate, onSignOut, className = '', onClose, showClose }) {
  // Sign out asks once: the first click arms it, a second click within 4 s signs out.
  const [confirmSignOut, setConfirmSignOut] = useState(false);
  useEffect(() => {
    if (!confirmSignOut) return undefined;
    const t = setTimeout(() => setConfirmSignOut(false), 4000);
    return () => clearTimeout(t);
  }, [confirmSignOut]);

  return (
    <aside className={className} style={{
      width: 'var(--sidebar-width)', flexShrink: 0, height: '100vh',
      position: showClose ? 'relative' : 'sticky', top: 0,
      background: 'var(--paper-2)', borderRight: '1px solid var(--hairline)',
      display: 'flex', flexDirection: 'column', padding: '28px 18px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 10px 32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 28, height: 28, borderRadius: 8, background: 'var(--blueprint)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <Zap size={15} color="#fff" strokeWidth={2.5} />
          </div>
          <span style={{ fontWeight: 700, fontSize: 18, letterSpacing: '-0.02em' }}>
            Afri<span style={{ color: 'var(--blueprint)' }}>Plan</span>
          </span>
        </div>
        {showClose && (
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--ink-muted)', cursor: 'pointer', padding: 4 }} aria-label="Close menu">
            <X size={20} />
          </button>
        )}
      </div>

      <nav className="app-nav" aria-label="Main">
        {NAV_GROUPS.map((group) => (
          <div key={group.title || 'home'}>
            {group.title && <div className="app-nav-group">{group.title}</div>}
            {group.items.map(({ page, label, step, icon: Icon }) => (
              <button
                key={page}
                type="button"
                className="app-nav-item"
                onClick={() => onNavigate(page)}
                aria-current={page === activePage ? 'page' : undefined}
              >
                <Icon size={17} strokeWidth={2} aria-hidden="true" />
                <span>{label}</span>
                {step && <span className="app-nav-step" aria-hidden="true">{step}</span>}
              </button>
            ))}
          </div>
        ))}
      </nav>

      <div className="app-user">
        <div className="app-user-who">
          <span className="app-user-avatar" aria-hidden="true">DE</span>
          <span>
            <strong>Demo Engineer</strong>
            <small>Demo mode</small>
          </span>
        </div>
        {/* The arrow points away from the door: leaving. Lucide's own LogOut reads as "go in". */}
        <button
          type="button"
          className={`app-signout${confirmSignOut ? ' is-armed' : ''}`}
          onClick={confirmSignOut ? onSignOut : () => setConfirmSignOut(true)}
        >
          <LogOut size={16} aria-hidden="true" style={{ transform: 'scaleX(-1)' }} />
          {confirmSignOut ? 'Confirm sign out' : 'Sign out'}
        </button>
      </div>
    </aside>
  );
}
