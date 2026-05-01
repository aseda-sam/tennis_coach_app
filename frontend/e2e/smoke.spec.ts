import { test, expect } from '@playwright/test';

// These run against localhost:3000 (docker compose up).
// VITE_PROFILE=local bypasses auth, so all protected routes are accessible.

test('root loads home page', async ({ page }) => {
  await page.goto('/');
  // Should not get a blank page or JS crash
  await expect(page.locator('body')).not.toBeEmpty();
  await expect(page).not.toHaveURL(/error/);
});

test('demo page loads without auth', async ({ page }) => {
  await page.goto('/demo');
  // Should render something — not redirect away
  await expect(page).toHaveURL(/\/demo/);
  await expect(page.locator('body')).not.toBeEmpty();
});

test('library page accessible locally (auth bypassed)', async ({ page }) => {
  await page.goto('/library');
  await expect(page).toHaveURL(/\/library/);
  await expect(page.locator('body')).not.toBeEmpty();
});

test('unknown route redirects to root', async ({ page }) => {
  await page.goto('/this-does-not-exist');
  await expect(page).toHaveURL('/');
});
