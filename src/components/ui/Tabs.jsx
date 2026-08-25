/* Simple controlled tab bar — introduced so content-dense pages (BoQ &
   quotation) can split a long single-scroll page into switchable sections
   instead of stacking everything vertically. Presentational only; the
   parent owns which tab is active and what renders under it. */
export default function Tabs({ tabs, active, onChange }) {
  return (
    <div role="tablist" style={{ display: 'flex', gap: 4, borderBottom: '1px solid var(--hairline)', marginBottom: 'var(--space-lg)', overflowX: 'auto' }}>
      {tabs.map((tab) => {
        const isActive = tab.id === active;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            style={{
              background: 'none', border: 'none', cursor: 'pointer', whiteSpace: 'nowrap',
              padding: '10px 16px', minHeight: 40, fontFamily: 'var(--sans)', fontSize: 14,
              fontWeight: isActive ? 600 : 500, color: isActive ? 'var(--blueprint-2)' : 'var(--ink-muted)',
              borderBottom: isActive ? '2px solid var(--blueprint-2)' : '2px solid transparent',
              marginBottom: -1, transition: 'color 0.15s ease, border-color 0.15s ease',
            }}
          >
            {tab.label}
            {typeof tab.count === 'number' && (
              <span style={{
                marginLeft: 7, fontFamily: 'var(--mono)', fontSize: 11,
                color: isActive ? 'var(--blueprint-2)' : 'var(--ink-muted)',
              }}>
                {tab.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
