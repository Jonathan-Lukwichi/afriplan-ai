import { useEffect, useState } from 'react';
import { api } from '../api/client';
import PageHeader from '../components/ui/PageHeader';
import MetricTile from '../components/ui/MetricTile';
import LineItemsTable from '../components/ui/LineItemsTable';
import GapReport from '../components/ui/GapReport';
import SectionSubtotalsChart from '../components/ui/SectionSubtotalsChart';

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
    return (
      <div style={{ padding: 'var(--space-xl)' }}>
        <p>No run selected.</p>
        <button onClick={() => onNavigate('upload')}>Upload a drawing</button>
      </div>
    );
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
    <div style={{ minHeight: '100vh', background: 'var(--paper)' }}>
      <div style={{ maxWidth: 860, margin: '0 auto', padding: 'var(--space-xl) var(--space-md)' }}>
        <PageHeader title="Generate the tender BoQ" subtitle="Fine-tune your pricing, then download the SANS 10142-1 compliant Excel and PDF." />

        {error && <p style={{ color: 'var(--rose)' }}>{error}</p>}

        <h3 style={{ fontSize: 16, marginBottom: 10 }}>Pricing</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, marginBottom: 'var(--space-md)' }}>
          <Field label="Markup %" value={markup} onChange={setMarkup} onBlur={refreshPreview} />
          <Field label="Contingency %" value={contingency} onChange={setContingency} onBlur={refreshPreview} />
          <Field label="VAT %" value={vat} onChange={setVat} onBlur={refreshPreview} />
          <div>
            <label style={{ fontSize: 13, color: 'var(--ink-muted)', display: 'block', marginBottom: 4 }}>Quote reference</label>
            <input value={quoteRef} onChange={(e) => setQuoteRef(e.target.value)} placeholder="auto" style={{ width: '100%', padding: 8, border: '1px solid var(--hairline-2)', borderRadius: 'var(--radius-sm)' }} />
          </div>
          <div>
            <label style={{ fontSize: 13, color: 'var(--ink-muted)', display: 'block', marginBottom: 4 }}>Validity (days)</label>
            <input type="number" value={validityDays} onChange={(e) => setValidityDays(Number(e.target.value))} onBlur={refreshPreview} style={{ width: '100%', padding: 8, border: '1px solid var(--hairline-2)', borderRadius: 'var(--radius-sm)' }} />
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
              <a href={api.boq.excelUrl(runId, exportParams)} style={downloadBtn}>Excel BoQ (.xlsx)</a>
              <a href={api.boq.pdfUrl(runId, exportParams)} style={downloadBtn}>PDF BoQ (.pdf)</a>
            </div>

            <h3 style={{ fontSize: 16, marginBottom: 10 }}>Email this BoQ</h3>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 10 }}>
              <input placeholder="client@example.com" value={emailTo} onChange={(e) => setEmailTo(e.target.value)} style={{ flex: '1 1 220px', padding: 8, border: '1px solid var(--hairline-2)', borderRadius: 'var(--radius-sm)' }} />
              <input placeholder="Recipient name (optional)" value={emailName} onChange={(e) => setEmailName(e.target.value)} style={{ flex: '1 1 180px', padding: 8, border: '1px solid var(--hairline-2)', borderRadius: 'var(--radius-sm)' }} />
              <button onClick={sendEmail} disabled={!emailTo || emailBusy} style={{ padding: '8px 20px', background: !emailTo || emailBusy ? 'var(--ink-muted)' : 'var(--blueprint)', color: 'white', border: 'none', borderRadius: 'var(--radius-sm)', fontWeight: 600, cursor: !emailTo || emailBusy ? 'not-allowed' : 'pointer' }}>
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
    </div>
  );
}

const downloadBtn = {
  padding: '10px 22px', background: 'transparent', color: 'var(--blueprint)',
  border: '1px solid var(--blueprint)', borderRadius: 'var(--radius-sm)', fontSize: 14,
  fontWeight: 600, textDecoration: 'none', display: 'inline-block',
};

function Field({ label, value, onChange, onBlur }) {
  return (
    <div>
      <label style={{ fontSize: 13, color: 'var(--ink-muted)', display: 'block', marginBottom: 4 }}>{label}</label>
      <input
        type="number" value={value} onChange={(e) => onChange(Number(e.target.value))} onBlur={onBlur}
        style={{ width: '100%', padding: 8, border: '1px solid var(--hairline-2)', borderRadius: 'var(--radius-sm)' }}
      />
    </div>
  );
}
