import { test, expect } from '@playwright/test';

test('ops dashboard renders responsive shell', async ({ page }) => {
  await page.route('**/health', route => route.fulfill({ json: { status: 'UP' } }));
  await page.route('**/api/v1/payments', route => route.fulfill({ json: [] }));
  await page.route('**/api/v1/ops/summary', route => route.fulfill({ json: { volumes_by_rail: {}, volumes_by_status: {}, unmatched_queue: [], refund_queue: [] } }));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Payments operations hub' })).toBeVisible();
  await expect(page.getByText('API UP')).toBeVisible();
});
