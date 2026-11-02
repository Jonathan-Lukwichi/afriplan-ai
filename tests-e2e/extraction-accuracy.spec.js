// A finished run shows its extraction accuracy when the project has a real bill on file, and hides
// the panel when it has none. The list of things to check keeps notes folded away. Fake API.
import { test, expect } from './fixtures.js';

const DXF = { name: 'L-01.dxf', mimeType: 'application/dxf', buffer: Buffer.from('0\nEOF\n') };

const GAPS = [
  { severity: 'high', description: 'Two feeders with no drawn route', assumption: 'Assumed 30 m.', suggested_action: 'Confirm the route.' },
  { severity: 'medium', description: 'Older revision not read', assumption: '', suggested_action: '' },
  { severity: 'low', description: 'Feeder lengths taken from the routes', assumption: '', suggested_action: '' },
];

const RUN = {
  run_id: 'demo', pipeline: 'dxf', status: 'passed', input_file: 'L-01.dxf', error: null,
  result: { boq: { total_items: 2, gaps: GAPS, total_incl_vat_zar: 1000 }, files: [], ai_symbols: [] },
};

const READING = {
  available: true, project: 'demo', reading_score: 0.74, coverage: 0.93, qty_accuracy: 0.79,
  items_judged: 29, items_found: 20, items_within_10pct: 11, item_precision: 0.83,
  biggest_misses: [{ item: '95mm2 x 4C cable', verdict: 'read 40 % short', points_lost: 0.116 }],
};

async function openRun(page, reading) {
  await page.route('**/api/runs', (r) => r.fulfill({ json: { run_id: 'demo', status: 'running' } }));
  await page.route('**/api/runs/demo', (r) => r.fulfill({ json: RUN }));
  await page.route('**/api/audit/reading/demo', (r) => r.fulfill({ json: reading }));
  await page.route('**/api/audit/coverage/demo', (r) => r.fulfill({ status: 404, json: {} }));
  await page.addInitScript(() => localStorage.setItem('afriplan_demo_authed', '1'));
  await page.goto('/#upload');
  await page.locator('input[type=file]').first().setInputFiles(DXF);
  await page.getByRole('button', { name: /Run .*engine|Run DXF|Start/ }).first().click();
}

test('a project with a real bill shows its extraction accuracy', async ({ page }) => {
  await openRun(page, READING);
  await expect(page.getByTestId('extraction-accuracy')).toHaveText('74.0 %');
  const panel = page.getByTestId('extraction-accuracy-panel');
  await expect(panel).toContainText('20 of 29');
  await expect(panel).toContainText('read 40 % short');
  await expect(page.getByText('Things to check', { exact: true })).toBeVisible();
  await panel.screenshot({ path: 'test-results/extraction-accuracy.png' });
});

test('a queried bill shows a second number, labelled as unconfirmed', async ({ page }) => {
  await openRun(page, { ...READING, if_queries_confirmed: { score: 0.9, items: ['The bill may count this cable twice.'] } });
  await expect(page.getByTestId('extraction-accuracy')).toHaveText('74.0 %');
  const second = page.getByTestId('accuracy-if-confirmed');
  await expect(second).toContainText('90.0 %');
  await expect(second).toContainText('not yet confirmed');
});

test('a project with no real bill shows no accuracy at all', async ({ page }) => {
  await openRun(page, { available: false });
  await expect(page.getByRole('button', { name: /View Bill of Quantities/ })).toBeVisible();
  await expect(page.getByTestId('extraction-accuracy-panel')).toHaveCount(0);
});
