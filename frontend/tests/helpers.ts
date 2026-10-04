import { expect, type Page, type Route } from '@playwright/test';

export const emptySummary = {
  business_date: '2026-10-04', payments_today: 0, volumes_by_rail: {}, volumes_by_status: {},
  unmatched_queue: [], refund_queue: [], pending_queue: [], retry_queue: [],
};

export async function signIn(page: Page, token: string) {
  await page.goto('/');
  await page.getByLabel('Access token').fill(token);
  await page.getByRole('button', { name: 'Sign in' }).click();
}

export const json = (route: Route, body: unknown, status = 200) => route.fulfill({ status, json: body });

export async function expectSignedInAs(page: Page, text: string) {
  await expect(page.getByText(text)).toBeVisible();
}
