import { useEffect, useState } from 'react';
import { api } from '../api/client';
import PageHeader from '../components/ui/PageHeader';
import MetricTile from '../components/ui/MetricTile';

/* Optional Step 4 — port of pages/4_Live_Pricing.py: request real supplier
   quotes for material lines, compare, apply the best one back into the
   bill (server-side, via RunRecord.sourced_boq), then an RFQ email channel
   for trade-counter suppliers with no online price. */
export default function Pricing({ runId, onNavigate }) {
  const [requests, setRequests] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [report, setReport] = useState(null);
  const [choices, setChoices] = useState({});
  const [applyResult, setApplyResult] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const [rfqSupplier, setRfqSupplier] = useState('');
  const [rfqDraft, setRfqDraft] = useState(null);
  const [rfqReply, setRfqReply] = useState('');
  const [rfqParsed, setRfqParsed] = useState(null);
  const [rfqError, setRfqError] = useState(null);

  useEffect(() => {
    if (!runId) return;
    api.pricing.getRequests(runId).then((data) => {
      setRequests(data.requests);
      setSuppliers(data.suppliers);
      setSelected(new Set(data.requests.slice(0, 15).map((r) => r.item_ref)));
      if (data.suppliers[0]) setRfqSupplier(data.suppliers[0].supplier_id);
    }).catch((e) => setError(e.message || 'Could not load this BoQ'));
  }, [runId]);

  if (!runId) {
    return (
      <div style={{ padding: 'var(--space-xl)' }}>
        <p>No run selected.</p>
        <button onClick={() => onNavigate('upload')}>Upload a drawing</button>
      </div>
    );
  }

  const toggle = (ref) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(ref) ? next.delete(ref) : next.add(ref);
      return next;
    });
  };

  const requestQuotes = async () => {
    setBusy(true);
    setError(null);
    try {
      const data = await api.pricing.requestQuotes(runId, Array.from(selected));
      setReport(data);
      const seeded = {};
      data.results.forEach((r) => { seeded[r.request.item_ref] = r.recommended_supplier_id || '__skip__'; });
      setChoices(seeded);
    } catch (e) {
      setError(e.message || 'Could not request quotes');
    } finally {
      setBusy(false);
    }
  };

  const applyQuotes = async () => {
    setBusy(true);
    try {
      const result = await api.pricing.apply(runId, choices);
      setApplyResult(result);
    } catch (e) {
      setError(e.message || 'Could not apply quotes');
    } finally {
      setBusy(false);
    }
  };

  const draftRfq = async () => {
    setRfqError(null);
    setRfqDraft(null);
    try {
      const draft = await api.pricing.draftRfq(runId, { item_refs: Array.from(selected), supplier_id: rfqSupplier });
      setRfqDraft(draft);
    } catch (e) {
      setRfqError(e.message || 'Could not draft the RFQ');
    }
  };

  const parseReply = async () => {
    setRfqError(null);
    setRfqParsed(null);
    try {
      const result = await api.pricing.parseRfqReply(runId, {
        item_refs: Array.from(selected), supplier_id: rfqSupplier, reply_text: rfqReply,
      });
      setRfqParsed(result.quotes);
    } catch (e) {
      setRfqError(e.message || 'Parsing failed');
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--paper)' }}>
      <div style={{ maxWidth: 900, margin: '0 auto', padding: 'var(--space-xl) var(--space-md)' }}>
        <PageHeader
          eyebrow="OPTIONAL · LIVE PRICING"
          title="Get real supplier prices for your BoQ"
          subtitle="Request live pricing, availability and lead times from multiple suppliers per item, then apply the best quote straight into the bill."
        />

        {error && <p style={{ color: 'var(--rose)' }}>{error}</p>}

        <h3 style={{ fontSize: 16, marginBottom: 10 }}>1 · Choose items</h3>
        <div style={{ maxHeight: 240, overflowY: 'auto', border: '1px solid var(--hairline-2)', borderRadius: 'var(--radius-sm)', marginBottom: 10 }}>
          {requests.map((r) => (
            <label key={r.item_ref} style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '6px 10px', fontSize: 13, borderBottom: '1px solid var(--hairline)' }}>
              <input type="checkbox" checked={selected.has(r.item_ref)} onChange={() => toggle(r.item_ref)} />
              {r.item_ref} · {r.description} ({r.qty}{r.unit})
            </label>
          ))}
        </div>
        <p style={{ fontSize: 12, color: 'var(--ink-muted)', marginBottom: 'var(--space-md)' }}>
          Panel: {suppliers.map((s) => s.name).join(' · ')} (simulated suppliers).
        </p>

        <button
          onClick={requestQuotes} disabled={!selected.size || busy}
          style={{ padding: '10px 22px', background: !selected.size || busy ? 'var(--ink-muted)' : 'var(--blueprint)', color: 'white', border: 'none', borderRadius: 'var(--radius-sm)', fontWeight: 600, cursor: !selected.size || busy ? 'not-allowed' : 'pointer', marginBottom: 'var(--space-lg)' }}
        >
          {busy ? 'Requesting…' : 'Request live quotes'}
        </button>

        {report && (
          <>
            <h3 style={{ fontSize: 16, marginBottom: 10 }}>2 · Compare &amp; choose</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 'var(--space-md)', marginBottom: 'var(--space-lg)' }}>
              <MetricTile label="Items sourced" value={report.items_sourced} />
              <MetricTile label="Suppliers contacted" value={report.suppliers_contacted} />
              <MetricTile label="Potential saving" value={`R ${report.potential_saving_zar.toLocaleString('en-ZA', { maximumFractionDigits: 0 })}`} />
            </div>

            {report.results.map((res) => (
              <div key={res.request.item_ref} style={{ border: '1px solid var(--hairline-2)', borderRadius: 'var(--radius-sm)', padding: 12, marginBottom: 10 }}>
                <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 8 }}>{res.request.item_ref} · {res.request.description}</div>
                <div style={{ overflowX: 'auto', marginBottom: 8 }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                    <thead>
                      <tr style={{ textAlign: 'left', color: 'var(--ink-muted)' }}>
                        <th style={{ padding: '4px 8px' }}>Supplier</th>
                        <th style={{ padding: '4px 8px' }}>Unit R</th>
                        <th style={{ padding: '4px 8px' }}>Availability</th>
                        <th style={{ padding: '4px 8px' }}>Lead (days)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {res.quotes.map((q) => (
                        <tr key={q.supplier_id} style={{ borderTop: '1px solid var(--hairline)' }}>
                          <td style={{ padding: '4px 8px' }}>{q.supplier_name}{q.supplier_id === res.recommended_supplier_id ? ' ★' : ''}</td>
                          <td style={{ padding: '4px 8px' }}>{q.unit_price_zar.toFixed(2)}</td>
                          <td style={{ padding: '4px 8px' }}>{q.availability.replace(/_/g, ' ')}</td>
                          <td style={{ padding: '4px 8px' }}>{q.lead_time_days}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <select
                  value={choices[res.request.item_ref] || '__skip__'}
                  onChange={(e) => setChoices((prev) => ({ ...prev, [res.request.item_ref]: e.target.value }))}
                  style={{ padding: 6, fontSize: 13, border: '1px solid var(--hairline-2)', borderRadius: 'var(--radius-sm)' }}
                >
                  <option value="__skip__">Keep BoQ estimate</option>
                  {res.quotes.map((q) => (
                    <option key={q.supplier_id} value={q.supplier_id}>{q.supplier_name} — R{q.unit_price_zar.toFixed(2)}</option>
                  ))}
                </select>
              </div>
            ))}

            <h3 style={{ fontSize: 16, margin: '18px 0 10px' }}>3 · Apply to BoQ</h3>
            <button
              onClick={applyQuotes} disabled={busy}
              style={{ padding: '10px 22px', background: busy ? 'var(--ink-muted)' : 'var(--emerald)', color: 'white', border: 'none', borderRadius: 'var(--radius-sm)', fontWeight: 600, cursor: busy ? 'not-allowed' : 'pointer' }}
            >
              Apply chosen supplier prices to the BoQ
            </button>
            {applyResult && (
              <div style={{ marginTop: 10 }}>
                <p style={{ fontSize: 13, color: 'var(--emerald)' }}>
                  Applied {applyResult.applied} line(s). Subtotal R {applyResult.subtotal_before_zar.toLocaleString('en-ZA')} → R {applyResult.subtotal_after_zar.toLocaleString('en-ZA')}.
                </p>
                <button onClick={() => onNavigate('boq')} style={{ padding: '8px 18px', background: 'transparent', color: 'var(--blueprint)', border: '1px solid var(--blueprint)', borderRadius: 'var(--radius-sm)', fontWeight: 600, cursor: 'pointer' }}>
                  Go to BoQ Generation to export →
                </button>
              </div>
            )}
          </>
        )}

        <h3 style={{ fontSize: 16, margin: '30px 0 10px' }}>RFQ email · trade-counter suppliers</h3>
        <p style={{ fontSize: 13, color: 'var(--ink-muted)', marginBottom: 10 }}>
          Suppliers who price on request. Draft a professional RFQ email for the selected items, send it, then paste their reply to parse it into structured quotes.
        </p>

        {rfqError && <p style={{ color: 'var(--rose)', fontSize: 13 }}>{rfqError}</p>}

        <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 10, flexWrap: 'wrap' }}>
          <select value={rfqSupplier} onChange={(e) => setRfqSupplier(e.target.value)} style={{ padding: 8, border: '1px solid var(--hairline-2)', borderRadius: 'var(--radius-sm)' }}>
            {suppliers.map((s) => <option key={s.supplier_id} value={s.supplier_id}>{s.name}</option>)}
          </select>
          <button onClick={draftRfq} disabled={!selected.size} style={{ padding: '8px 18px', background: !selected.size ? 'var(--ink-muted)' : 'var(--blueprint)', color: 'white', border: 'none', borderRadius: 'var(--radius-sm)', fontWeight: 600, cursor: !selected.size ? 'not-allowed' : 'pointer' }}>
            Draft RFQ
          </button>
        </div>

        {rfqDraft && (
          <div style={{ marginBottom: 'var(--space-md)' }}>
            <div style={{ fontSize: 12, color: 'var(--ink-muted)' }}>To: {rfqDraft.to}</div>
            <div style={{ fontSize: 12, color: 'var(--ink-muted)', marginBottom: 6 }}>Subject: {rfqDraft.subject}</div>
            <textarea readOnly value={rfqDraft.body} rows={8} style={{ width: '100%', padding: 8, fontSize: 12, fontFamily: 'var(--mono)', border: '1px solid var(--hairline-2)', borderRadius: 'var(--radius-sm)' }} />
          </div>
        )}

        <textarea
          placeholder="Paste the supplier's emailed reply here"
          value={rfqReply} onChange={(e) => setRfqReply(e.target.value)}
          rows={5} style={{ width: '100%', padding: 8, fontSize: 13, border: '1px solid var(--hairline-2)', borderRadius: 'var(--radius-sm)', marginBottom: 8 }}
        />
        <button
          onClick={parseReply} disabled={!rfqReply.trim()}
          style={{ padding: '8px 18px', background: !rfqReply.trim() ? 'var(--ink-muted)' : 'var(--blueprint)', color: 'white', border: 'none', borderRadius: 'var(--radius-sm)', fontWeight: 600, cursor: !rfqReply.trim() ? 'not-allowed' : 'pointer' }}
        >
          Parse reply into quotes
        </button>

        {rfqParsed && (
          <div style={{ overflowX: 'auto', marginTop: 10 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: 'var(--paper-2)', textAlign: 'left' }}>
                  {['Item', 'Unit R', 'Availability', 'Lead (days)', 'Confidence'].map((h) => (
                    <th key={h} style={{ padding: '6px 10px' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rfqParsed.map((q, i) => (
                  <tr key={i} style={{ borderTop: '1px solid var(--hairline)' }}>
                    <td style={{ padding: '6px 10px' }}>{q.item_ref}</td>
                    <td style={{ padding: '6px 10px' }}>{q.unit_price_zar}</td>
                    <td style={{ padding: '6px 10px' }}>{q.availability}</td>
                    <td style={{ padding: '6px 10px' }}>{q.lead_time_days}</td>
                    <td style={{ padding: '6px 10px' }}>{Math.round(q.parse_confidence * 100)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
