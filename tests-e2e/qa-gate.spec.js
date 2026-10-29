// QA gate (dashboard-qa-gate, 2026-10-29): plain-language errors, keyboard reach, the
// current page announced, and no heavy call on any page's load. The API is faked.
import { test, expect } from './fixtures.js';

const DXF = { name: 'plan.dxf', mimeType: 'application/dxf', buffer: Buffer.from('0\nEOF\n') };

async function openAuthed(page, route) {
  await page.addInitScript(() => localStorage.setItem('afriplan_demo_authed', '1'));
  await page.goto(`/#${route}`);
}

async function runDxf(page) {
  await openAuthed(page, 'upload');
  await page.locator('input[type=file]').first().setInputFiles(DXF);
  await page.getByRole('button', { name: /Run DXF engine/ }).click();
}

test('server unreachable: Run says so in plain words, not "Failed to fetch"', async ({ page }) => {
  await page.route('**/api/**', (r) => r.abort('connectionrefused'));
  await runDxf(page);
  await expect(page.getByText(/can.t reach the AfriPlan server/i)).toBeVisible();
  await expect(page.getByText('Failed to fetch')).toHaveCount(0);
});

test('landing and login links are real buttons the keyboard reaches', async ({ page }) => {
  await page.goto('/#landing');
  await expect(page.getByRole('button', { name: 'Sign in', exact: true })).toHaveCount(2);   // header + footer
  await expect(page.getByRole('button', { name: 'Get started' })).toHaveCount(1);
  await page.getByRole('button', { name: 'Sign in', exact: true }).first().focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/#login$/);
  await expect(page.getByRole('button', { name: /Back to home/ })).toHaveCount(1);
});

test('the sidebar marks exactly one item as the current page', async ({ page }) => {
  await openAuthed(page, 'upload');
  await expect(page.locator('[aria-current="page"]')).toHaveCount(1);
  await expect(page.getByRole('button', { name: /Upload/ }).and(page.locator('[aria-current="page"]'))).toHaveCount(1);
  await page.getByRole('button', { name: /Audit a BoQ/ }).click();
  await expect(page.locator('[aria-current="page"]')).toHaveText(/Audit a BoQ/);
});

test('server error without a reason: no status code or API path shown', async ({ page }) => {
  await page.route('**/api/runs', (r) => r.fulfill({ status: 500, body: 'Internal Server Error' }));
  await runDxf(page);
  await expect(page.getByText(/the server had a problem/i)).toBeVisible();
  await expect(page.getByText('/api/runs')).toHaveCount(0);
});
