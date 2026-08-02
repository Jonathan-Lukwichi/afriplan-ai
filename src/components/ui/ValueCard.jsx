/* Glass-card feature tile with a gradient icon badge (lucide-react icon,
   not emoji) — matches the Robotiko/Dashdark reference's card treatment. */
export default function ValueCard({ icon: Icon, title, body }) {
  return (
    <div className="glass-card" style={{ padding: 'var(--space-md)', transition: 'transform 0.2s ease, border-color 0.2s ease' }}>
      <div style={{
        width: 44, height: 44, borderRadius: 12, background: 'var(--gradient-primary)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 14,
      }}>
        <Icon size={22} color="#05070F" strokeWidth={2.25} />
      </div>
      <h3 style={{ fontSize: 17, marginBottom: 8 }}>{title}</h3>
      <p style={{ fontSize: 14, color: 'var(--ink-muted)', margin: 0, lineHeight: 1.55 }}>{body}</p>
    </div>
  );
}
