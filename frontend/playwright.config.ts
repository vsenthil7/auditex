import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  timeout: 300_000,       // 5 min per test
  retries: 0,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'tests/results/html-report', open: 'never' }],
  ],
  use: {
    baseURL: 'http://localhost:3000',
    headless: false,
    viewport: { width: 1280, height: 800 },
    video: 'retain-on-failure',
    screenshot: 'only-on-failure',
    // No actionTimeout — let waitForTimeout in while-loop run freely
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
  ],
  tsconfig: './tests/tsconfig.json',
})
