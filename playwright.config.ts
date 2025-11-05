// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

const BASE_URL = process.env.WEB_BASE_URL ?? 'http://localhost:3000';
// Change this to whatever actually starts your app.
// If your start script needs no flags, just use: 'npm start'
const WEB_CMD  = process.env.PW_WEBSERVER_CMD || 'npm start -- --port 3000 --host';

export default defineConfig({
  // Only look at UI tests
  testDir: 'tests/ui',
  // Only run *.spec.* so it won't pick up *.test.ts used by Jest
  testMatch: ['**/*.spec.@(ts|js)'],
  // Explicitly ignore the API folder
  testIgnore: ['**/tests/api/**'],

  // Start a local server when using the localhost fallback
  webServer: BASE_URL.startsWith('http://localhost:')
    ? {
        command: WEB_CMD,
        url: BASE_URL,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      }
    : undefined,

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
