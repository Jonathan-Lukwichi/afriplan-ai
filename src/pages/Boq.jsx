import { useEffect, useState } from 'react';
import { api } from '../api/client';
import PageHeader from '../components/ui/PageHeader';
import MetricTile from '../components/ui/MetricTile';
import LineItemsTable from '../components/ui/LineItemsTable';
import GapReport from '../components/ui/GapReport';
import SectionSubtotalsChart from '../components/ui/SectionSubtotalsChart';
import EmptyState from '../components/ui/EmptyState';
import Tabs from '../components/ui/Tabs';
import FindingsTable from '../components/ui/FindingsTable';
import Glossary from '../components/ui/Glossary';

const inputStyle = {
  width: '100%', padding: 10, background: 'rgba(255,255,255,0.03)',
  border: '1px solid var(--hairline-2)', borderRadius: 'var(--radius-sm)', color: 'var(--ink)', fontSize: 14,
};

/* Step 3 — port of the original app's pages/3_BOQ_Generation.py: pick
   pricing, preview the priced bill, download Excel/PDF/JSON, or email it
   to a client (new — the original had download buttons only). */
export default function Boq({ runId, onNavigate }) {
  // Estimator rates already include the x1.3 material markup, so the default
  // EXTRA markup is 0 — the profile's markup is not applied a second time.
  const [markup, setMarkup] = useState(0);
  // Derived items (wall boxes, chasing, conduit, wire, terminations) from fitted
  // ratios — offered only when a ratio model exists on this server.
  const [ratioModel, setRatioModel] = useState(null);
  const [complete, setComplete] = useState(false);
  const [audit, setAudit] = useState(null);
  const [contingency, setContingency] = useState(5);
  const [vat, setVat] = useState(15);
  const [quoteRef, setQuoteRef] = useState('');
  const [validityDays, setValidityDays] = useState(30);
  const [priced, setPriced] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  const [emailTo, setEmailTo] = useState('');
  const [emailName, setEmailName] = useState('');
  const [emailBusy, setEmailBusy] = useState(false);
  const [emailResult, setEmailResult] = useState(null);

  useEffect(() => {
    api.boq.getProfile().then((p) => {
      setContingency(p.contingency_pct);
      setVat(p.vat_pct);
    }).catch(() => {});
    api.audit.ratioModel().then((m) => {
      setRatioModel(m);
      if (m.available) setComplete(true);
    }).catch(() => setRatioModel({ available: false }));
  }, []);

  const refreshPreview = () => {
    if (!runId) return;
    setError(null);
    setAudit(null);
    api.boq.json(runId, { markup, contingency, vat, complete })
      .then(setPriced)
      .catch((e) => setError(e.message || 'Could not load the priced BoQ'));
  };

  useEffect(() => { refreshPreview(); }, [runId, complete]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (activeTab !== 'audit' || !runId || audit) return;
    api.audit.run(runId, { complete })
      .then(setAudit)
      .catch((e) => setAudit({ error: e.message }));
  }, [activeTab, runId, complete, audit]);

  if (!runId) {
    return <EmptyState message="No run selected." actionLabel="Upload a drawing" onAction={() => onNavigate('upload')} />;
  }

  const exportParams = { markup, contingency, vat, complete, quote_ref: quoteRef, validity_days: validityDays };

  const sendEmail = async () => {
    if (!emailTo) return;
    setEmailBusy(true);
    setEmailResult(null);
    try {
      const result = await api.boq.email({
        run_id: runId, to: emailTo, recipient_name: emailName || null,
        markup, contingency, vat, complete, quote_ref: quoteRef || null, validity_days: validityDays,
      });
      setEmailResult(result);
    } catch (e) {
      setEmailResult({ sent: false, error: e.message });
    } finally {
      setEmailBusy(false);
    }
  };

  return (
    <div style={{ maxWidth: 1440, padding: 'var(--space-xl) var(--space-md)' }}>
      <PageHeader title="BoQ & quotation" subtitle="Set your margin and tax, review the SANS 10142-1 checked bill, then send the quotation from here." />

      {error && <p style={{ color: 'var(--rose)' }}>{error}</p>}

      <h3 style={{ fontSize: 16, marginBottom: 10 }}>Pricing</h3>
      <div className="glass-card" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, padding: 'var(--space-md)', marginBottom: 'var(--space-md)' }}>
        <Field label="Extra markup %" value={markup} onChange={setMarkup} onBlur={refreshPreview}
               title="Rates already include material markup (x1.3) and labour. Add extra margin only if intended." />
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

      {ratioModel?.available && (
        <label className="glass-card" style={{ display: 'flex', gap: 10, alignItems: 'flex-start', padding: 'var(--space-md)', marginBottom: 'var(--space-md)', cursor: 'pointer' }}>
          <input type="checkbox" checked={complete} onChange={(e) => setComplete(e.target.checked)} style={{ marginTop: 3 }} data-testid="complete-toggle" />
          <span style={{ fontSize: 14 }}>
            <strong>Complete with derived items</strong> — wall boxes, chasing, conduit, wire, terminations.
            <span style={{ display: 'block', color: 'var(--ink-muted)', fontSize: 13, marginTop: 2 }}>
              Items never drawn as symbols, added from ratios fitted on a real priced project
              ({ratioModel.project_sources?.join(', ')}). Each added line is marked <em>Worked out</em> and
              listed under “Things to check” — verify before tendering.
            </span>
          </span>
        </label>
      )}

      {priced && (
        <>
          <Glossary />
          <Tabs
            tabs={[
              { id: 'overview', label: 'Overview' },
              { id: 'items', label: 'Line items', count: priced.total_items },
              { id: 'gaps', label: 'Things to check', count: priced.gaps?.length ?? 0 },
              { id: 'audit', label: 'Audit', count: audit?.summary?.count },
              { id: 'export', label: 'Export & email' },
            ]}
            active={activeTab}
            onChange={setActiveTab}
          />

          {activeTab === 'overview' && (
            <div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 'var(--space-md)', marginBottom: 'var(--space-lg)' }}>
                <MetricTile label="Subtotal" value={`R ${priced.subtotal_zar.toLocaleString('en-ZA', { maximumFractionDigits: 0 })}`} />
                <MetricTile label="Total ex VAT" value={`R ${priced.total_excl_vat_zar.toLocaleString('en-ZA', { maximumFractionDigits: 0 })}`} />
                <MetricTile label="VAT" value={`R ${priced.vat_zar.toLocaleString('en-ZA', { maximumFractionDigits: 0 })}`} />
                <MetricTile label="Total incl. VAT" value={`R ${priced.total_incl_vat_zar.toLocaleString('en-ZA', { maximumFractionDigits: 0 })}`} />
              </div>

              <h3 style={{ fontSize: 16, marginBottom: 10 }}>Section subtotals</h3>
              <SectionSubtotalsChart subtotals={priced.section_subtotals_short} />
            </div>
          )}

          {activeTab === 'audit' && (
            <div>
              <p style={{ fontSize: 13, color: 'var(--ink-muted)', marginBottom: 10 }}>
                Checks this bill for arithmetic errors, unpriced lines, duplicates and feeders
                missing their earth, terminations or install line.
              </p>
              {!audit && <p style={{ fontSize: 14 }}>Auditing…</p>}
              {audit?.error && <p style={{ color: 'var(--rose)' }}>{audit.error}</p>}
              {audit?.findings && <FindingsTable findings={audit.findings} />}
            </div>
          )}

          {activeTab === 'items' && (
            <div>
              <h3 style={{ fontSize: 16, marginBottom: 10 }}>Line items ({priced.total_items})</h3>
              <LineItemsTable items={priced.line_items} />
            </div>
          )}

          {activeTab === 'gaps' && (
            <div>
              {priced.gaps?.length ? (
                <GapReport gaps={priced.gaps} />
              ) : (
                <p style={{ fontSize: 14, color: 'var(--ink-muted)' }}>Nothing to check — every line was read from the drawings or worked out from them.</p>
              )}
            </div>
          )}

          {activeTab === 'export' && (
            <div>
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
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Field({ label, value, onChange, onBlur, title }) {
  return (
    <div title={title}>
      <label style={{ fontSize: 13, color: 'var(--ink-muted)', display: 'block', marginBottom: 4 }}>{label}</label>
      <input type="number" value={value} onChange={(e) => onChange(Number(e.target.value))} onBlur={onBlur} style={inputStyle} />
    </div>
  );
}
