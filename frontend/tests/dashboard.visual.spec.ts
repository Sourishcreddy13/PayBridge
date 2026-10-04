import { expect, test } from '@playwright/test';
import { emptySummary, json, signIn } from './helpers';

test('dashboard visual baseline', async ({ page }) => {
  await page.route('**/health', (r) => json(r, { status: 'UP' }));
  await page.route('**/api/v1/me', (r) => json(r, { subject: 'olivia', role: 'OPS' }));
  await page.route('**/api/v1/payments', (r) => json(r, [
    { payment_id: '11111111-aaaa-bbbb-cccc-000000000001', state: 'SETTLED', amount: '1500.00', currency: 'INR', rail: 'UPI', created_at: '2026-10-04T05:00:00Z' },
    { payment_id: '22222222-aaaa-bbbb-cccc-000000000002', state: 'PENDING', amount: '250000.00', currency: 'INR', rail: 'RTGS', created_at: '2026-10-04T05:30:00Z' },
  ]));
  await page.route('**/api/v1/ops/summary**', (r) => json(r, {
    ...emptySummary, payments_today: 2, volumes_by_rail: { UPI: 1, RTGS: 1 }, volumes_by_status: { SETTLED: 1, PENDING: 1 },
    pending_queue: [{ payment_id: '22222222-aaaa-bbbb-cccc-000000000002', rail: 'RTGS', amount: '250000.00', created_at: '2026-10-04T05:30:00Z' }],
  }));
  await page.clock.setFixedTime(new Date('2026-10-04T06:00:00Z'));
  await signIn(page, 'ops-token');
  await expect(page.getByLabel('Today metric')).toContainText('2');
  await expect(page).toHaveScreenshot('dashboard.png', { animations: 'disabled', fullPage: true });
});
