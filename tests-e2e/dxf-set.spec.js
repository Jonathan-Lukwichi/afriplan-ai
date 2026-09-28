// A whole DWG drawing set uploaded in the browser, run as ONE project: feeders on the
// SLDs are measured on the electrical site plan (issue 002). Needs the backend running
// (VITE_API_BASE_URL baked into the build) and the client's drawings, which are local
// only (gitignored) — so the test skips itself anywhere they are missing.
import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const DIR = process.env.DWG_SET_DIR || path.resolve('data/projects/wedela/raw/Wedela Electrical');
const API = process.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

test('upload a DWG set and see feeders measured on the site plan', async ({ page, request }) => {
  test.setTimeout(300_000);
  test.skip(!fs.existsSync(DIR), 'drawing set not present (client data is local only)');
  const health = await request.get(`${API}/api/health`).catch(() => null);
  test.skip(!health || !health.ok(), 'backend not running');

  // the whole folder, older revision included — the app must skip it by itself
  const files = fs.readdirSync(DIR).filter((f) => f.toLowerCase().endsWith('.dwg'))
    .map((f) => path.join(DIR, f));
  expect(files.length).toBeGreaterThan(10);

  // same filter as responsive.spec.js: offline external assets are not app errors
  const IGNORED = /Failed to load resource|net::ERR|favicon|load failed/i;
  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error' && !IGNORED.test(m.text())) errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.addInitScript(() => localStorage.setItem('afriplan_demo_authed', '1'));
  await page.goto('/#upload');

  await page.getByTestId('dxf-files').setInputFiles(files);
  await expect(page.getByText(`${files.length} drawings — read together as one project`, { exact: false })).toBeVisible();
  await page.getByRole('button', { name: /Run DXF engine/ }).click();

  const panel = page.getByTestId('drawing-set-panel');
  await expect(panel).toBeVisible({ timeout: 240_000 });
  await expect(panel.getByText(/Feeder routes measured on WD-OL-001/)).toBeVisible();
  await expect(panel.getByText('site plan', { exact: true })).toBeVisible();
  await expect(panel.getByText(/skipped — older revision — replaced by WD-PB-01-LIGHTING\s+100425/)).toBeVisible();
  await page.screenshot({ path: 'screenshots/dxf-set-result.png', fullPage: true });

  await page.getByRole('button', { name: /View Bill of Quantities/ }).click();
  await page.getByRole('tab', { name: /Line items/ }).click().catch(() => page.getByText(/^Line items/).first().click());
  await expect(page.getByText(/SWA feeder MINI-SUB→KIOSK/).first()).toBeVisible({ timeout: 30_000 });
  expect(errors, errors.join('\n')).toEqual([]);
});
