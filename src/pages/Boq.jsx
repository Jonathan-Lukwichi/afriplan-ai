import { useEffect, useState } from 'react';
import { api } from '../api/client';
import PageHeader from '../components/ui/PageHeader';
import MetricTile from '../components/ui/MetricTile';
import LineItemsTable from '../components/ui/LineItemsTable';
import GapReport from '../components/ui/GapReport';
import SectionSubtotalsChart from '../components/ui/SectionSubtotalsChart';
import EmptyState from '../components/ui/EmptyState';

const inputStyle = {
  width: '100%', padding: 10, background: 'rgba(255,255,255,0.03)',
  border: '1px solid var(--hairline-2)', borderRadius: 'var(--radius-sm)', color: 'var(--ink)', fontSize: 14,
};

/* Step 3 — port of the original app's pages/3_BOQ_Generation.py: pick
   pricing, preview the priced bill, download Excel/PDF/JSON, or email it
   to a client (new — the original had download buttons only). */
export default function Boq({ runId, onNavigate }) {
  const [markup, setMarkup] = useState(20);
  const [contingency, setContingency] = useState(5);
  const [vat, setVat] = useState(15);
  const [quoteRef, setQuoteRef] = useState('');
  const [validityDays, setValidityDays] = useState(30);
  const [priced, setPriced] = useState(null);
  const [error, setError] = useState(null);

  const [emailTo, setEmailTo] = useState('');
  const [emailName, setEmailName] = useState('');
  const [emailBusy, setEmailBusy] = useState(false);
  const [emailResult, setEmailResult] = useState(null);

  useEffect(() => {
    api.boq.getProfile().then((p) => {
      setMarkup(p.markup_pct);
      setContingency(p.contingency_pct);
      setVat(p.vat_pct);
    }).catch(() => {});
  }, []);

  const refreshPreview = () => {
    if (!runId) return;
    setError(null);
    api.boq.json(runId, { markup, contingency, vat })
      .then(setPriced)
      .catch((e) => setError(e.message || 'Could not load the priced BoQ'));
  };

  useEffect(() => { refreshPreview(); }, [runId]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!runId) {
    return <EmptyState message="No run selected." actionLabel="Upload a drawing" onAction={() => onNavigate('upload')} />;
  }

  const exportParams = { markup, contingency, vat, quote_ref: quoteRef, validity_days: validityDays };

  const sendEmail = async () => {
    if (!emailTo) return;
    setEmailBusy(true);
    setEmailResult(null);
    try {
      const result = await api.boq.email({
        run_id: runId, to: emailTo, recipient_name: emailName || null,
        markup, contingency, vat, quote_ref: quoteRef || null, validity_days: validityDays,
      });
      setEmailResult(result);
    } catch (e) {
      setEmailResult({ sent: false, error: e.message });
    } finally {
      setEmailBusy(false);
    }
  };

  return (
    <div style={{ maxWidth: 860, padding: 'var(--space-xl) var(--space-md)' }}>
      <PageHeader title="BoQ & quotation" subtitle="Set your margin and tax, review the SANS 10142-1 checked bill, then send the quotation from here." />

      {error && <p style={{ color: 'var(--rose)' }}>{error}</p>}

      <h3 style={{ fontSize: 16, marginBottom: 10 }}>Pricing</h3>
      <div className="glass-card" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, padding: 'var(--space-md)', marginBottom: 'var(--space-md)' }}>
        <Field label="Markup %" value={markup} onChange={setMarkup} onBlur={refreshPreview} />
        <Field label="Contingency %" value={contingency} onChange={setContingency} onBlur={refreshPreview} />
        <Field label="VAT %" value={vat} onChange={setVat} onBlur={refreshPreview} />
        <div>
          <label style={{ fontSize: 13, color: 'var(--ink-muted)', display: 'block', marginBottom: 4 }}>Quote reference</label>
          <input value={quoteRef} onChange={(e) => setQuoteRef(e.target.value)} placeholder="auto" style={inputStyle} />
        </div>
        <div>
          <label style={{ fontSize: 13, color: 'var(--ink-muted)', display: 'block', marginBottom: 4 }}>Validity (days)</label>
          <input type="number" value={validityDays} onChange={(e) => setValidityDays(Number(e.target.value))} onBlur={refreshPreview} style={inputStyle} />
        </div>
      </div>

      {priced && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 'var(--space-md)', marginBottom: 'var(--space-lg)' }}>
            <MetricTile label="Subtotal" value={`R ${priced.subtotal_zar.toLocaleString('en-ZA', { maximumFractionDigits: 0 })}`} />
            <MetricTile label="Total ex VAT" value={`R ${priced.total_excl_vat_zar.toLocaleString('en-ZA', { maximumFractionDigits: 0 })}`} />
            <MetricTile label="VAT" value={`R ${priced.vat_zar.toLocaleString('en-ZA', { maximumFractionDigits: 0 })}`} />
            <MetricTile label="Total incl. VAT" value={`R ${priced.total_incl_vat_zar.toLocaleString('en-ZA', { maximumFractionDigits: 0 })}`} />
          </div>

          <h3 style={{ fontSize: 16, marginBottom: 10 }}>Section subtotals</h3>
          <SectionSubtotalsChart subtotals={priced.section_subtotals_short} />

          <h3 style={{ fontSize: 16, marginBottom: 10 }}>Line items ({priced.total_items})</h3>
          <div style={{ marginBottom: 'var(--space-lg)' }}>
            <LineItemsTable items={priced.line_items} />
          </div>

          <GapReport gaps={priced.gaps} />

          <h3 style={{ fontSize: 16, marginBottom: 10 }}>Downloads</h3>
          <div style={{ display: 'flex', gap: 10, marginBottom: 'var(--space-xl)', flexWrap: 'wrap' }}>
            <a href={api.boq.excelUrl(runId, exportParams)} className="btn-ghost" style={{ textDecoration: 'none', fontSize: 14 }}>Excel BoQ (.xlsx)</a>
            <a href={api.boq.pdfUrl(runId, exportParams)} className="btn-ghost" style={{ textDecoration: 'none', fontSize: 14 }}>Quotation (.pdf)</a>
          </div>

          <p style={{ fontSize: 13, marginBottom: 'var(--space-lg)' }}>
            <button onClick={() => onNavigate('pricing')} style={{ background: 'none', border: 'none', color: 'var(--blueprint-2)', fontWeight: 600, cursor: 'pointer', padding: 0, fontSize: 13 }}>
              Get real supplier prices for this BoQ →
            </button>
          </p>

          <h3 style={{ fontSize: 16, marginBottom: 10 }}>Email this BoQ</h3>
          <div className="glass-card" style={{ display: 'flex', gap: 10, flexWrap: 'wrap', padding: 'var(--space-md)', marginBottom: 10 }}>
            <input placeholder="client@example.com" value={emailTo} onChange={(e) => setEmailTo(e.target.value)} style={{ ...inputStyle, flex: '1 1 220px' }} />
            <input placeholder="Recipient name (optional)" value={emailName} onChange={(e) => setEmailName(e.target.value)} style={{ ...inputStyle, flex: '1 1 180px' }} />
            <button onClick={sendEmail} disabled={!emailTo || emailBusy} className="btn-gradient" style={{ padding: '10px 22px', fontSize: 14 }}>
              {emailBusy ? 'Sending…' : 'Send'}
            </button>
          </div>
          {emailResult && (
            <p style={{ fontSize: 13, color: emailResult.sent ? 'var(--emerald)' : 'var(--rose)' }}>
              {emailResult.sent ? `Sent: "${emailResult.subject}"` : `Not sent${emailResult.error ? `: ${emailResult.error}` : ' — email provider not configured'}`}
            </p>
          )}
        </>
      )}
    </div>
  );
}

function Field({ label, value, onChange, onBlur }) {
  return (
    <div>
      <label style={{ fontSize: 13, color: 'var(--ink-muted)', display: 'block', marginBottom: 4 }}>{label}</label>
      <input type="number" value={value} onChange={(e) => onChange(Number(e.target.value))} onBlur={onBlur} style={inputStyle} />
    </div>
  );
}
