import { useState } from 'react';
import {
  FileText, GitCompare, Home, Layers, LogOut, Menu, Upload as UploadIcon, Wallet, X, Zap,
} from 'lucide-react';
import headerBanner from '../../assets/images/header-banner-goldenhour.jpg';

const NAV_ITEMS = [
  { page: 'welcome', label: 'Welcome', icon: Home },
  { page: 'upload', label: 'Upload', icon: UploadIcon },
  { page: 'extraction', label: 'Extraction', icon: Layers },
  { page: 'compare', label: 'Compare', icon: GitCompare },
  { page: 'boq', label: 'BoQ', icon: FileText },
  { page: 'pricing', label: 'Pricing', icon: Wallet },
];

/* Persistent authenticated-app layout: icon-labeled sidebar (nav between
   every in-app page) + a photo header banner shared across all of them,
   replacing the old pattern of each page being a lone full-bleed <div>
   with its own ad-hoc "back to X" button. */
export default function AppShell({ activePage, onNavigate, onSignOut, children }) {
  const [drawerOpen, setDrawerOpen] = useState(false);

  const go = (page) => {
    onNavigate(page);
    setDrawerOpen(false);
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--paper)', display: 'flex' }}>
      <Sidebar activePage={activePage} onNavigate={go} onSignOut={onSignOut} className="app-sidebar" />

      {drawerOpen && (
        <>
          <div
            onClick={() => setDrawerOpen(false)}
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 40 }}
          />
          <div style={{ position: 'fixed', top: 0, left: 0, bottom: 0, zIndex: 50, width: 'var(--sidebar-width)' }}>
            <Sidebar activePage={activePage} onNavigate={go} onSignOut={onSignOut} onClose={() => setDrawerOpen(false)} showClose />
          </div>
        </>
      )}

      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
        {/* Persistent header banner — real photo across every in-app page */}
        <div style={{ position: 'relative', height: 84, flexShrink: 0, overflow: 'hidden' }}>
          <img src={headerBanner} alt="" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center 30%' }} />
          <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(90deg, rgba(10,14,26,0.94), rgba(10,14,26,0.75) 60%, rgba(10,14,26,0.5))' }} />
          <div style={{ position: 'relative', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 var(--space-md)' }}>
            <button
              className="app-mobile-topbar"
              onClick={() => setDrawerOpen(true)}
              style={{ display: 'none', background: 'none', border: 'none', color: 'var(--ink)', cursor: 'pointer', padding: 8, alignItems: 'center', justifyContent: 'center' }}
              aria-label="Open menu"
            >
              <Menu size={22} />
            </button>
            <div style={{ fontFamily: 'var(--mono)', fontSize: 12, letterSpacing: '0.12em', color: 'var(--circuit-2)' }}>
              DUAL-PIPELINE · SANS 10142-1:2017
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13, color: 'var(--ink-2)' }}>
              <div style={{ width: 30, height: 30, borderRadius: '50%', background: 'var(--gradient-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 12, color: '#05070F' }}>
                DM
              </div>
              <span className="navbar-link-wide">Demo Contractor</span>
            </div>
          </div>
        </div>

        <div style={{ flex: 1, overflowY: 'auto' }}>
          {children}
        </div>
      </div>
    </div>
  );
}

function Sidebar({ activePage, onNavigate, onSignOut, className = '', onClose, showClose }) {
  return (
    <aside className={className} style={{
      width: 'var(--sidebar-width)', flexShrink: 0, height: '100vh', position: showClose ? 'relative' : 'sticky', top: 0,
      background: 'var(--paper-2)', borderRight: '1px solid var(--hairline)',
      display: 'flex', flexDirection: 'column', padding: 'var(--space-md)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-lg)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: 'var(--gradient-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <Zap size={17} color="#05070F" strokeWidth={2.5} />
          </div>
          <span style={{ fontWeight: 800, fontSize: 15 }}>AfriPlan</span>
        </div>
        {showClose && (
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--ink-muted)', cursor: 'pointer', padding: 4 }} aria-label="Close menu">
            <X size={20} />
          </button>
        )}
      </div>

      <nav style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: 1 }}>
        {NAV_ITEMS.map(({ page, label, icon: Icon }) => {
          const active = page === activePage;
          return (
            <button
              key={page}
              onClick={() => onNavigate(page)}
              style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: '11px 14px', minHeight: 44,
                background: active ? 'var(--gradient-primary)' : 'transparent',
                color: active ? '#05070F' : 'var(--ink-2)',
                border: 'none', borderRadius: 'var(--radius-sm)', fontSize: 14, fontWeight: active ? 700 : 500,
                cursor: 'pointer', textAlign: 'left', transition: 'background 0.15s ease',
              }}
              onMouseEnter={(e) => { if (!active) e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
              onMouseLeave={(e) => { if (!active) e.currentTarget.style.background = 'transparent'; }}
            >
              <Icon size={18} strokeWidth={2.25} />
              {label}
            </button>
          );
        })}
      </nav>

      <div style={{ borderTop: '1px solid var(--hairline)', paddingTop: 'var(--space-md)', display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--gradient-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 12, color: '#05070F', flexShrink: 0 }}>
          DM
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>Demo Contractor</div>
          <div style={{ fontSize: 11, color: 'var(--ink-muted)' }}>Demo mode</div>
        </div>
        <button onClick={onSignOut} style={{ background: 'none', border: 'none', color: 'var(--ink-muted)', cursor: 'pointer', padding: 6 }} aria-label="Sign out">
          <LogOut size={17} />
        </button>
      </div>
    </aside>
  );
}
