// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

const BASE_URL = process.env.DJANGO_BASE_URL ?? 'http://127.0.0.1:8000';

export default defineConfig({
  // Only look at UI tests
  testDir: 'tests/ui',
  // Only run *.spec.* so it won't pick up *.test.ts used by Jest
  testMatch: ['**/*.spec.@(ts|js)'],
  // Explicitly ignore the API folder
  testIgnore: ['**/tests/api/**'],

  use: {
    baseURL: BASE_URL,               // ← makes page.goto('/') valid
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox',  use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit',   use: { ...devices['Desktop Safari'] } },
  ],

  reporter: [
    ['list'],
    ['html',  { outputFolder: 'playwright-report', open: 'never' }],
    ['junit', { outputFile: 'reports/junit/playwright.xml' }],
  ],
});
