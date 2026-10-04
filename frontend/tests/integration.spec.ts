// End-to-end against the REAL FastAPI backend (see webServer in playwright.config.ts).
import { expect, test, type Page } from '@playwright/test';
import { TOKENS } from '../playwright.config';
import { signIn } from './helpers';

const API = 'http://127.0.0.1:8000';
const bearer = (token: string) => ({ Authorization: `Bearer ${token}` });
const stamp = Date.now();

async function startPayment(page: Page, name: string, amount: string) {
  await page.getByLabel('Beneficiary name').fill(name);
  await page.getByLabel('Account number').fill('123456789012');
  await page.getByLabel('IFSC').fill('ABCD0123456');
  await page.getByLabel('Amount (₹)').fill(amount);
  await page.getByLabel('Narration').fill('e2e invoice');
  await page.getByRole('button', { name: 'Initiate payment' }).click();
}

test.describe.serial('customer and operations journeys on the real backend', () => {
  let paymentId = '';

  test('customer initiates a payment and sees it routed and PENDING', async ({ page }) => {
    await signIn(page, TOKENS.alice);
    await expect(page.getByRole('heading', { name: 'My payments' })).toBeVisible();
    await startPayment(page, `Alice Vendor ${stamp}`, '1500.00');
    await expect(page.getByRole('status')).toContainText('routed via UPI');
    await expect(page.getByRole('heading', { name: /^Payment [0-9a-f]{8}$/ })).toBeVisible();
    await expect(page.locator('.detail .status')).toHaveText('PENDING');
    // Masked values only: the raw account number never comes back to the browser.
    await expect(page.locator('.detail')).not.toContainText('123456789012');
    const list = await page.request.get(`${API}/api/v1/payments`, { headers: bearer(TOKENS.alice) });
    paymentId = (await list.json())[0].payment_id;
  });

  test('another customer cannot see it (object-level authorization)', async ({ request }) => {
    expect((await request.get(`${API}/api/v1/payments/${paymentId}`, { headers: bearer(TOKENS.bob) })).status()).toBe(404);
    expect((await request.get(`${API}/api/v1/payments/${paymentId}`, { headers: bearer(TOKENS.alice) })).status()).toBe(200);
    expect((await request.post(`${API}/api/v1/payments/${paymentId}/process`, { headers: bearer(TOKENS.alice) })).status()).toBe(403);
  });

  test('operator processes the payment from the dashboard', async ({ page }) => {
    await signIn(page, TOKENS.ops);
    await expect(page.getByRole('heading', { name: 'Payments operations hub' })).toBeVisible();
    await expect(page.getByLabel('Volume by rail')).toContainText('UPI');
    const queue = page.getByLabel('Awaiting processing');
    await expect(queue).toContainText(paymentId.slice(0, 8));
    await queue.getByRole('button', { name: 'Process' }).first().click();
    await expect(page.getByRole('status')).toContainText('Processed');
    await expect(page.getByLabel('Volume by status')).toContainText('SETTLED');
  });

  test('customer tracks status and timeline, then requests a refund', async ({ page }) => {
    await signIn(page, TOKENS.alice);
    await page.getByRole('button', { name: `Open payment ${paymentId.slice(0, 8)}` }).click();
    await expect(page.locator('.detail .status')).toHaveText('SETTLED');
    await expect(page.locator('.timeline')).toContainText('PENDING → PROCESSING');
    await expect(page.locator('.timeline')).toContainText('PROCESSING → SETTLED');
    await page.getByRole('button', { name: 'Request full refund' }).click();
    await expect(page.getByTestId('refund-status')).toContainText('completed');
    await expect(page.locator('.detail .status')).toHaveText('REFUNDED');
  });

  test('ops sees the refund and can import, reconcile and settle a business date', async ({ page }) => {
    await signIn(page, TOKENS.ops);
    await expect(page.getByLabel('Refund queue')).toContainText('COMPLETED');
    const csv = `external_reference,payment_id,amount,currency\nbank-${stamp},,999.00,INR\n`;
    await page.getByLabel('Inbound settlement file (CSV)').setInputFiles({ name: 'inbound.csv', mimeType: 'text/csv', buffer: Buffer.from(csv) });
    await expect(page.getByRole('status')).toContainText('Imported inbound.csv');
    await page.getByRole('button', { name: 'Reconcile' }).click();
    await expect(page.getByLabel('Unmatched queue')).toContainText(`bank-${stamp}`);
    await page.getByRole('button', { name: 'Generate settlement' }).click();
    await expect(page.getByRole('status')).toContainText('Settlement file generated');
    await page.getByRole('button', { name: 'Generate settlement' }).click();
    await expect(page.getByRole('alert')).toContainText('already exists');
  });

  test('an invalid token is rejected by the real API', async ({ page }) => {
    await signIn(page, 'not-a-real-token');
    await expect(page.getByRole('alert')).toContainText('not accepted');
  });
});
