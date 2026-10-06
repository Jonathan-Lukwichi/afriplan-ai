// A slow PDF run shows where it is (step, pages, time, the AI's "busy, waiting" note) and a
// failed one shows the real reason. The API is faked here, so no AI quota is used.
import { test, expect } from '@playwright/test';

const PDF = { name: 'set.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4\n%%EOF') };

async function startPdfRun(page, poll) {
  await page.route('**/api/runs', (r) => r.fulfill({ json: { run_id: 'demo', status: 'running' } }));
  await page.route('**/api/runs/demo', (r) => r.fulfill({ json: poll() }));
  await page.addInitScript(() => localStorage.setItem('afriplan_demo_authed', '1'));
  await page.goto('/#upload');
  await page.getByRole('button', { name: 'PDF', exact: false }).first().click();
  await page.locator('input[type=file][accept=".pdf"]').setInputFiles(PDF);
  await page.getByRole('button', { name: /Run PDF engine/ }).click();
}

test('a running PDF job shows its step, pages, time and the AI wait', async ({ page }) => {
  await startPdfRun(page, () => ({
    run_id: 'demo', pipeline: 'pdf', status: 'running', input_file: '2 files', error: null, result: null,
    progress: { stage: 'read', done: 7, total: 18, elapsed_s: 252,
                message: 'Reading the drawings: 7 of 18 pages read by the AI',
                note: 'Gemini busy (free tier limit per minute) - waiting 41 s, attempt 2 of 6' },
  }));
  const box = page.getByTestId('run-progress');
  await expect(box).toContainText('Reading the drawings: 7 of 18 pages');
  await expect(box).toContainText('7 / 18 pages');
  await expect(box).toContainText('4 min 12 s');
  await expect(box).toContainText('waiting 41 s');
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '39');
  await page.screenshot({ path: 'test-results/run-progress.png', fullPage: false });
});

test('a failed PDF job shows the real reason, not "no billable items"', async ({ page }) => {
  const why = "The AI could not read 18 of 18 pages: Gemini's free daily limit is used up for gemini-2.5-flash";
  await startPdfRun(page, () => ({
    run_id: 'demo', pipeline: 'pdf', status: 'failed', input_file: '2 files', error: why, result: null, progress: null,
  }));
  await expect(page.getByText(why)).toBeVisible();
});

test('a run waiting in line says so, with no steps or page count yet', async ({ page }) => {
  await startPdfRun(page, () => ({
    run_id: 'demo', pipeline: 'pdf', status: 'running', input_file: '2 files', error: null, result: null,
    progress: { stage: 'queued', done: 0, total: 0, elapsed_s: 75,
                message: 'Waiting in line: 2 runs ahead of yours',
                note: 'The server runs a few projects at a time so that no run is lost.' },
  }));
  const box = page.getByTestId('run-progress');
  await expect(box).toContainText('Waiting in line: 2 runs ahead of yours');
  await expect(box).toContainText('waiting for 1 min 15 s');
  await expect(box).not.toContainText('Read drawings');
});

test('an upload refused because the server is busy shows the reason', async ({ page }) => {
  const busy = 'AfriPlan is busy: 2 PDF run(s) in progress and 20 waiting. Please try again in a few minutes.';
  await page.route('**/api/runs', (r) => r.fulfill({ status: 503, json: { detail: busy } }));
  await page.addInitScript(() => localStorage.setItem('afriplan_demo_authed', '1'));
  await page.goto('/#upload');
  await page.getByRole('button', { name: 'PDF', exact: false }).first().click();
  await page.locator('input[type=file][accept=".pdf"]').setInputFiles(PDF);
  await page.getByRole('button', { name: /Run PDF engine/ }).click();
  await expect(page.getByText(busy)).toBeVisible();
});
