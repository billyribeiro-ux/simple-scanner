import { expect, test } from '@playwright/test';

test('dashboard loads', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Live signal command center' })).toBeVisible();
});

test('scanner page exposes start and stop controls', async ({ page }) => {
  await page.goto('/scanner');
  await expect(page.getByRole('button', { name: /Start/ })).toBeVisible();
  await expect(page.getByRole('button', { name: /Stop/ })).toBeVisible();
});

test('provider operations page is data-only', async ({ page }) => {
  await page.goto('/operations/provider');
  await expect(page.getByRole('heading', { name: 'FMP Provider' })).toBeVisible();
  await expect(page.getByRole('button', { name: /Capability/ })).toBeVisible();
  await expect(page.getByText(/No broker execution/)).toBeVisible();
  await expect(page.getByRole('button', { name: /Buy|Sell|Submit order/i })).toHaveCount(0);
});

test('data operations page shows coverage surface', async ({ page }) => {
  await page.goto('/operations/data');
  await expect(page.getByRole('heading', { name: 'Data Operations' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Latest bars' })).toBeVisible();
});
