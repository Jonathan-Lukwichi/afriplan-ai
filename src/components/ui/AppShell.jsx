import { useEffect, useState } from 'react';
import {
  ChevronLeft, FileText, GitCompare, Home, Layers, LogOut, Menu, ShieldCheck, Upload as UploadIcon, Wallet, X, Zap,
} from 'lucide-react';

const NAV_ITEMS = [
  { page: 'welcome', label: 'Welcome', step: '01', icon: Home },
  { page: 'upload', label: 'Upload', step: '02', icon: UploadIcon },
  { page: 'extraction', label: 'Take-off', step: '03', icon: Layers },
  { page: 'compare', label: 'Compare', step: '04', icon: GitCompare },
  { page: 'boq', label: 'BoQ', step: '05', icon: FileText },
  { page: 'pricing', label: 'Pricing', step: '06', icon: Wallet },
  { page: 'audit', label: 'Audit a BoQ', step: '07', icon: ShieldCheck },
];

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
        <Sidebar activePage={activePage} onNavigate={go} onSignOut={onSignOut} onCollapse={onToggle} className="app-sidebar" />
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
        <div style={{
          height: 52, flexShrink: 0, background: '#16203C',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          gap: 16, padding: '0 clamp(16px, 3vw, 36px)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 18, minWidth: 0 }}>
            <button
              onClick={onToggle}
              aria-label={sidebarOpen ? 'Hide menu' : 'Show menu'}
              title={sidebarOpen ? 'Hide menu' : 'Show menu'}
              style={{
                width: 30, height: 30, borderRadius: 7, flexShrink: 0,
                border: '1px solid rgba(255,255,255,0.18)', background: 'rgba(255,255,255,0.08)',
                color: '#FCFCFD', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'background 0.15s ease',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.16)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; }}
            >
              <Menu size={16} />
            </button>
            <span style={{
              fontFamily: 'var(--mono)', fontSize: 12, letterSpacing: '0.12em', color: '#9FB0D6',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}>
              TAKE-OFF ENGINE
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexShrink: 0 }}>
            <span style={{
              fontFamily: 'var(--mono)', fontSize: 12, color: '#9FB0D6',
              border: '1px solid rgba(255,255,255,0.18)', borderRadius: 6, padding: '4px 10px',
            }}>
              ZAR
            </span>
            <span className="navbar-link-wide" style={{ fontSize: 13, color: '#C7CEE2' }}>Demo Engineer</span>
          </div>
        </div>

        <div style={{ flex: 1, overflowY: 'auto' }}>
          {children}
        </div>
      </div>
    </div>
  );
}

function Sidebar({ activePage, onNavigate, onSignOut, className = '', onClose, showClose, onCollapse }) {
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
        {!showClose && onCollapse && (
          <button
            onClick={onCollapse}
            aria-label="Collapse sidebar"
            title="Collapse sidebar"
            style={{
              background: 'none', border: '1px solid var(--hairline)', borderRadius: 7, width: 26, height: 26,
              color: 'var(--ink-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0, transition: 'background 0.15s ease, color 0.15s ease',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(16,26,51,0.05)'; e.currentTarget.style.color = 'var(--ink)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'none'; e.currentTarget.style.color = 'var(--ink-muted)'; }}
          >
            <ChevronLeft size={15} />
          </button>
        )}
      </div>

      <nav style={{ display: 'flex', flexDirection: 'column', gap: 2, flex: 1 }}>
        {NAV_ITEMS.map(({ page, label, step, icon: Icon }) => {
          const active = page === activePage;
          return (
            <button
              key={page}
              onClick={() => onNavigate(page)}
              style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px', minHeight: 44,
                background: active ? '#FFFFFF' : 'transparent',
                border: active ? '1px solid rgba(46,91,232,0.28)' : '1px solid transparent',
                boxShadow: active ? '0 1px 2px rgba(16,26,51,0.05)' : 'none',
                color: active ? 'var(--ink)' : 'var(--ink-2)',
                borderRadius: 'var(--radius-sm)', fontFamily: 'var(--sans)', fontSize: 15,
                fontWeight: active ? 600 : 400, cursor: 'pointer', textAlign: 'left',
                transition: 'background 0.15s ease',
              }}
              onMouseEnter={(e) => { if (!active) e.currentTarget.style.background = 'rgba(16,26,51,0.035)'; }}
              onMouseLeave={(e) => { if (!active) e.currentTarget.style.background = 'transparent'; }}
            >
              <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: active ? 'var(--blueprint)' : 'var(--ink-muted)' }}>{step}</span>
              <Icon size={17} strokeWidth={2} />
              {label}
            </button>
          );
        })}
      </nav>

      <div style={{ borderTop: '1px solid var(--hairline)', paddingTop: 18, display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ width: 34, height: 34, borderRadius: '50%', background: 'var(--ink)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 600, fontSize: 12, color: '#fff', flexShrink: 0 }}>
          DE
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 14, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>Demo Engineer</div>
          <div style={{ fontSize: 12, color: 'var(--ink-muted)' }}>Demo mode</div>
        </div>
        <button onClick={onSignOut} style={{ background: 'none', border: 'none', color: 'var(--ink-muted)', cursor: 'pointer', padding: 6 }} aria-label="Sign out">
          <LogOut size={17} />
        </button>
      </div>
    </aside>
  );
}
