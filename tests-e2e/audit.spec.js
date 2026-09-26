// Audit-a-BoQ end-to-end: real browser → React page → FastAPI → api/audit.
// Needs the backend running (VITE_API_BASE_URL baked into the build) and the
// client's reference workbook, which is local-only (gitignored) — so the test
// skips itself on CI or any machine without them, instead of failing.
import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const XLSX = process.env.AUDIT_XLSX
  || path.resolve('data/projects/wedela/raw/Wedela BOQ Rev01 141125.xlsx');
const API = process.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

test('audit a real BOQ workbook in the browser', async ({ page, request }) => {
  test.skip(!fs.existsSync(XLSX), 'reference workbook not present (client data is local only)');
  const health = await request.get(`${API}/api/health`).catch(() => null);
  test.skip(!health || !health.ok(), 'backend not running');

  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  await page.addInitScript(() => localStorage.setItem('afriplan_demo_authed', '1'));
  await page.goto('/#audit');

  await expect(page.getByRole('heading', { name: 'Audit a Bill of Quantities' })).toBeVisible();
  await page.getByTestId('audit-file').setInputFiles(XLSX);
  await page.getByRole('button', { name: 'Audit this BoQ' }).click();

  const table = page.getByTestId('findings-table');
  await expect(table).toBeVisible({ timeout: 30_000 });
  const rows = await table.locator('tbody tr').count();
  expect(rows).toBeGreaterThan(10);
  await expect(page.getByText('NOT_IN_SUMMARY').first()).toBeVisible();
  await expect(page.getByText('Bills read from the workbook')).toBeVisible();
  await page.screenshot({ path: 'screenshots/audit-result.png', fullPage: true });
  expect(errors, errors.join('\n')).toEqual([]);
});
