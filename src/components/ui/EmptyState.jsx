import { Inbox } from 'lucide-react';

/* Shared "nothing to show yet" state for Extraction/Compare/Boq/Pricing when
   no run/comparison is selected. */
export default function EmptyState({ message, actionLabel, onAction }) {
  return (
    <div className="glass-card" style={{ padding: 'var(--space-xl)', textAlign: 'center', maxWidth: 420 }}>
      <div style={{
        width: 48, height: 48, borderRadius: 12, background: 'rgba(255,255,255,0.05)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px',
      }}>
        <Inbox size={22} color="var(--ink-muted)" strokeWidth={1.75} />
      </div>
      <p style={{ fontSize: 14, color: 'var(--ink-muted)', marginBottom: 'var(--space-md)' }}>{message}</p>
      <button onClick={onAction} className="btn-gradient" style={{ fontSize: 15 }}>
        {actionLabel}
      </button>
    </div>
  );
}
