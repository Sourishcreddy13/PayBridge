// Isolated UI tests with a mocked backend: component behaviour and error paths only.
// End-to-end behaviour against the real backend lives in integration.spec.ts.
import { expect, test } from '@playwright/test';
import { emptySummary, json, signIn } from './helpers';

const mockApi = async (page: import('@playwright/test').Page, role: 'OPS' | 'CUSTOMER', summary: unknown = emptySummary) => {
  await page.route('**/health', (r) => json(r, { status: 'UP' }));
  await page.route('**/api/v1/me', (r) => json(r, { subject: 'tester', role }));
  await page.route('**/api/v1/payments', (r) => json(r, []));
  await page.route('**/api/v1/ops/summary**', (r) => json(r, summary));
};

test('sign-in is required and a rejected token is reported', async ({ page }) => {
  await page.route('**/health', (r) => json(r, { status: 'UP' }));
  await page.route('**/api/v1/me', (r) => json(r, { error: 'Invalid bearer token' }, 401));
  await signIn(page, 'wrong-token');
  await expect(page.getByRole('alert')).toContainText('not accepted');
  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible();
});

test('ops dashboard renders rail and status volumes and queues', async ({ page }) => {
  await mockApi(page, 'OPS', {
    ...emptySummary, payments_today: 7,
    volumes_by_rail: { UPI: 4, RTGS: 3 }, volumes_by_status: { SETTLED: 5, PENDING: 2 },
    unmatched_queue: [{ external_reference: 'bank-9', payment_id: null, amount: '10.00', currency: 'INR', status: 'UNMATCHED' }],
    pending_queue: [{ payment_id: 'aaaaaaaa-0000-0000-0000-000000000000', rail: 'UPI', amount: '10.00', created_at: '2026-10-04T05:00:00Z' }],
  });
  await signIn(page, 'ops-token');
  await expect(page.getByRole('heading', { name: 'Payments operations hub' })).toBeVisible();
  await expect(page.getByText('API UP')).toBeVisible();
  await expect(page.getByLabel('Today metric')).toContainText('7');
  await expect(page.getByLabel('Volume by rail')).toContainText('UPI');
  await expect(page.getByLabel('Volume by rail')).toContainText('RTGS');
  await expect(page.getByLabel('Volume by status')).toContainText('SETTLED');
  await expect(page.getByLabel('Unmatched queue')).toContainText('bank-9');
  await expect(page.getByLabel('Awaiting processing').getByRole('button', { name: 'Process' })).toBeVisible();
});

test('backend failures surface as an alert instead of a blank page', async ({ page }) => {
  await page.route('**/health', (r) => json(r, { status: 'UP' }));
  await page.route('**/api/v1/me', (r) => json(r, { subject: 'olivia', role: 'OPS' }));
  await page.route('**/api/v1/payments', (r) => json(r, { error: 'internal_error' }, 500));
  await page.route('**/api/v1/ops/summary**', (r) => json(r, { error: 'internal_error' }, 500));
  await signIn(page, 'ops-token');
  await expect(page.getByRole('alert')).toContainText('internal_error');
});

test('customers get the customer portal, not the ops tools', async ({ page }) => {
  await mockApi(page, 'CUSTOMER');
  await signIn(page, 'customer-token');
  await expect(page.getByRole('heading', { name: 'My payments' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'New payment' })).toBeVisible();
  await expect(page.getByText('Settlement & reconciliation')).toHaveCount(0);
});
