import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests-e2e',
  timeout: 60_000,
  // One browser at a time. In parallel, `vite preview` on Windows took 10-20 s to serve each
  // page (measured 2026-10-29: run-progress.spec.js 4/4 failed with 2 or 4 workers, 4/4 passed
  // with 1 in 14 s). Cause not found; fonts and a stale server were ruled out.
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:4173',
  },
  webServer: {
    command: 'npx vite preview --port 4173 --strictPort --host 127.0.0.1',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
