// Things to check as questions: answering one updates the bill, and it can be undone. Fake API.
import { test, expect } from './fixtures.js';

const DXF = { name: 'L-01.dxf', mimeType: 'application/dxf', buffer: Buffer.from('0\nEOF\n') };
const QID = 'feeder:DBA>DBC';

const question = (status, answer = null) => ({
  id: QID, group: 'no_route', title: 'DB-A→DB-C: 35 mm² cable', why: 'Assumed 30 m.', action: 'Confirm.', severity: 'high',
  fields: [{ name: 'length_m', label: 'Cable length', unit: 'm', value: 30, required: true },
           { name: 'trench_m', label: 'Trench length (0 if not in a trench)', unit: 'm', value: 30, required: false }],
  options: [], on_bill_zar: 38000, per_unit_zar: 1258, per_unit: 'metre', status, answer,
});

const review = (status, answer, change) => ({
  available: true, open: status === 'answered' ? 1 : 2, answered: status === 'answered' ? 1 : 0, recheck: 0,
  reader_subtotal_zar: 1000000, subtotal_zar: 1000000 + change, change_zar: change, total_incl_vat_zar: 1207500 + change,
  groups: [
    { key: 'no_route', title: 'Feeders with no drawn route', bulk: null, open: status === 'answered' ? 0 : 1, questions: [question(status, answer)] },
    { key: 'legend', title: 'In the legend, not found on any plan', bulk: { label: 'None of these are on the plans', values: { qty: 0 } }, open: 1,
      questions: [{ id: 'legend:Geyser', group: 'legend', title: 'Geyser', why: '', action: '', severity: 'medium',
                    fields: [{ name: 'qty', label: 'How many', unit: '', value: 0, required: true }], options: [],
                    on_bill_zar: 0, per_unit_zar: 0, per_unit: '', status: 'open', answer: null }] },
  ],
});

const RUN = {
  run_id: 'demo', pipeline: 'dxf', status: 'passed', input_file: 'L-01.dxf', error: null,
  result: { boq: { total_items: 1, gaps: [], total_incl_vat_zar: 1207500 }, files: [], ai_symbols: [] },
};

const BILL = {
  subtotal_zar: 1000000, total_excl_vat_zar: 1050000, vat_zar: 157500, total_incl_vat_zar: 1207500, total_items: 1,
  section_subtotals_short: {}, gaps: [{ severity: 'low', description: 'A note about feeders', assumption: '', suggested_action: '' }],
  line_items: [{ item_no: 1, section: 'SECTION 8: CABLE CONTAINMENT', description: '20mm PVC conduit', unit: 'm', qty: 10,
                 unit_price_zar: 37, total_zar: 370, source: 'assumed', source_label: 'Measured, ceiling assumed' }],
};

async function openBill(page, onAnswer) {
  let current = review('open', null, 0);
  await page.route('**/api/runs', (r) => r.fulfill({ json: { run_id: 'demo', status: 'running' } }));
  await page.route('**/api/runs/demo', (r) => r.fulfill({ json: RUN }));
  await page.route('**/api/audit/**', (r) => r.fulfill({ status: 404, json: {} }));
  await page.route('**/api/export/json/demo**', (r) => r.fulfill({ json: BILL }));
  await page.route('**/api/review/demo/answers**', (r) => {
    const body = r.request().method() === 'PUT' ? r.request().postDataJSON() : null;
    if (body) onAnswer?.(body);
    current = body ? review('answered', { values: body.values, by: 'the estimator', at: 'now' }, 12500) : review('open', null, 0);
    return r.fulfill({ json: current });
  });
  await page.route('**/api/review/demo', (r) => r.fulfill({ json: current }));
  await page.addInitScript(() => localStorage.setItem('afriplan_demo_authed', '1'));
  await page.goto('/#upload');
  await page.locator('input[type=file]').first().setInputFiles(DXF);
  await page.getByRole('button', { name: /Run .*engine|Run DXF|Start/ }).first().click();
  await page.getByRole('button', { name: /View Bill of Quantities/ }).click();
  await page.getByRole('tab', { name: /Things to check/ }).or(page.getByRole('button', { name: /Things to check/ })).first().click();
}

test('an answer updates the bill and can be undone', async ({ page }) => {
  const sent = [];
  await openBill(page, (b) => sent.push(b));
  const card = page.getByTestId(`question-${QID}`);
  await expect(card).toContainText('R 38');
  await card.getByLabel(/Cable length/).fill('55');
  await card.getByRole('button', { name: 'Save answer' }).click();
  await expect(page.getByTestId('review-change')).toContainText('12');
  expect(sent[0]).toMatchObject({ question_id: QID, values: { length_m: 55, trench_m: 30 } });

  await page.getByTestId(`question-${QID}`).getByRole('button', { name: 'Undo' }).click();
  await expect(page.getByTestId('review-change')).toHaveCount(0);
});

test('a group can be answered in one click', async ({ page }) => {
  const sent = [];
  await openBill(page, (b) => sent.push(b));
  const group = page.getByTestId('group-legend');
  await group.locator('summary').click();
  await group.getByRole('button', { name: 'None of these are on the plans' }).click();
  await expect.poll(() => sent.length).toBe(1);
  expect(sent[0]).toMatchObject({ question_id: 'legend:Geyser', values: { qty: 0 } });
});

test('notes stay folded away below the questions', async ({ page }) => {
  await openBill(page);
  await expect(page.getByTestId('gaps-notes')).toContainText('For information');
  await expect(page.getByTestId('gaps-to-check')).toHaveCount(0);
});

test('a measured line says what it rests on', async ({ page }) => {
  await openBill(page);
  await page.getByRole('tab', { name: /Line items/ }).or(page.getByRole('button', { name: /Line items/ })).first().click();
  await expect(page.getByText('Measured, ceiling assumed')).toBeVisible();
});
