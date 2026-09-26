// Dev: Vite on :5173 talks to the API on :8000. Production: the API serves
// the built frontend itself, so requests are same-origin (empty base).
// See engineering-webapp-skills' engineering-webapp-scaffold skill.
const API_BASE = import.meta.env.VITE_API_BASE_URL
  || (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '');

async function request(path, { method = 'GET', body, signal } = {}) {
  const opts = { method, signal };
  if (body instanceof FormData) {
    opts.body = body;
  } else if (body !== undefined) {
    opts.headers = { 'Content-Type': 'application/json' };
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(`${API_BASE}${path}`, opts);
  if (!res.ok) {
    let detail = null;
    try { detail = await res.json(); } catch { try { detail = await res.text(); } catch {} }
    const err = new Error(`${res.status} ${res.statusText} — ${path}`);
    err.status = res.status;
    err.detail = detail;
    throw err;
  }
  return res.json();
}

export const api = {
  health: (signal) => request('/api/health', { signal }),

  runs: {
    // `files` is a single File (dxf) or an array of Files (pdf, multi-drawing).
    create: (files, pipeline = 'dxf') => {
      const form = new FormData();
      (Array.isArray(files) ? files : [files]).forEach((f) => form.append('files', f));
      form.append('pipeline', pipeline);
      return request('/api/runs', { method: 'POST', body: form });
    },
    get: (runId, signal) => request(`/api/runs/${runId}`, { signal }),
  },

  compare: {
    create: (dxfFile, pdfFiles) => {
      const form = new FormData();
      form.append('dxf_file', dxfFile);
      pdfFiles.forEach((f) => form.append('pdf_files', f));
      return request('/api/compare', { method: 'POST', body: form });
    },
    get: (compareId, signal) => request(`/api/compare/${compareId}`, { signal }),
    pdfUrl: (compareId) => `${API_BASE}/api/compare/${compareId}/pdf`,
  },

  boq: {
    getProfile: (signal) => request('/api/boq/profile', { signal }),
    saveProfile: (profile) => request('/api/boq/profile', { method: 'PUT', body: profile }),
    json: (runId, params, signal) => request(`/api/export/json/${runId}?${new URLSearchParams(params)}`, { signal }),
    excelUrl: (runId, params) => `${API_BASE}/api/export/excel/${runId}?${new URLSearchParams(params)}`,
    pdfUrl: (runId, params) => `${API_BASE}/api/export/pdf/${runId}?${new URLSearchParams(params)}`,
    email: (payload) => request('/api/export/email', { method: 'POST', body: payload }),
  },

  audit: {
    // Audit any priced BOQ workbook (.xlsx) — no run needed.
    boq: (file) => {
      const form = new FormData();
      form.append('file', file);
      return request('/api/audit/boq', { method: 'POST', body: form });
    },
    run: (runId, params = {}, signal) => request(`/api/audit/run/${runId}?${new URLSearchParams(params)}`, { signal }),
    coverage: (runId, signal) => request(`/api/audit/coverage/${runId}`, { signal }),
    ratioModel: (signal) => request('/api/audit/ratio-model', { signal }),
  },

  pricing: {
    getRequests: (runId, signal) => request(`/api/pricing/requests/${runId}`, { signal }),
    requestQuotes: (runId, itemRefs) => request(`/api/pricing/quotes/${runId}`, { method: 'POST', body: { item_refs: itemRefs } }),
    getQuotes: (runId, signal) => request(`/api/pricing/quotes/${runId}`, { signal }),
    apply: (runId, choices) => request(`/api/pricing/apply/${runId}`, { method: 'POST', body: { choices } }),
    draftRfq: (runId, payload) => request(`/api/pricing/rfq/draft/${runId}`, { method: 'POST', body: payload }),
    parseRfqReply: (runId, payload) => request(`/api/pricing/rfq/parse/${runId}`, { method: 'POST', body: payload }),
  },
};
