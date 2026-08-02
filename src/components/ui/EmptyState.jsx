/* Shared "nothing to show yet" state for Extraction/Compare/Boq/Pricing when
   no run/comparison is selected. Was previously copy-pasted per page as a
   bare, unstyled <button> — caught by the responsive E2E harness as a
   21px-tall tap target, well under the WCAG 2.5.8 24px AA floor. */
export default function EmptyState({ message, actionLabel, onAction }) {
  return (
    <div style={{ padding: 'var(--space-xl)' }}>
      <p style={{ fontSize: 14, color: 'var(--ink-muted)', marginBottom: 'var(--space-md)' }}>{message}</p>
      <button
        onClick={onAction}
        style={{
          padding: '12px 26px', background: 'var(--blueprint)', color: 'white',
          border: 'none', borderRadius: 'var(--radius-sm)', fontSize: 15,
          fontWeight: 600, cursor: 'pointer', minHeight: 44,
        }}
      >
        {actionLabel}
      </button>
    </div>
  );
}
