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

  // Populated as each later build phase lands:
  // compare: { get: (a, b) => request(`/api/compare?a=${a}&b=${b}`) },
  // export: { excel: (runId) => `${API_BASE}/api/export/excel/${runId}`, pdf: (runId) => `${API_BASE}/api/export/pdf/${runId}` },
};
