import { test, expect } from '@playwright/test';

test('homepage loads and shows title', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/NHS - Help to stay healthy/i); 
  await expect(page.locator('body')).toContainText(/Get help to make healthy lifestyle changes that last/i);
});
