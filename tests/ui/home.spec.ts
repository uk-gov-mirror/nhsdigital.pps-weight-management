import { test, expect } from '@playwright/test';

test('homepage loads and shows title', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/Pilot access/i); 
  // await expect(page.locator('body')).toContainText(/Help to stay healthy/i);
});
