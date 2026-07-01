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
