import { test, expect } from '@playwright/test';

test('homepage loads and shows title', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/PPS Weight Management/i); 
  await expect(page.locator('body')).toContainText(/Hello World!/i);
});

test('Public Ping button shows pong', async ({ page }) => {
  await page.goto('/');

  const button = page.getByRole('button', { name: /public ping/i });
  const output = page.locator('#out');

  await expect(button).toBeVisible();

  // Click and wait for the actual ping response
  const [resp] = await Promise.all([
    page.waitForResponse(r => r.url().includes('/public/api/ping')),
    button.click(),
  ]);

  // Network sanity check (optional but helpful in CI)
  expect(resp.status(), 'ping endpoint should return 200').toBe(200);

  // UI shows the response text
  await expect(output).toHaveText(/pong/i, { timeout: 10_000 });
});
