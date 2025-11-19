import { test, expect } from '@playwright/test';

test('homepage loads and shows title', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/NHS/i); 
  await expect(page.locator('body')).toContainText(/Welcome to the Weight management home page/i);
});
