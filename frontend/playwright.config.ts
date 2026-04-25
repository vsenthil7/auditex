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
    // Demo-mode toggles (set DEMO=1 env to slow + record; otherwise normal CI run)
    viewport: process.env.DEMO === '1' ? { width: 1440, height: 900 } : { width: 1280, height: 800 },
    video: process.env.DEMO === '1' ? 'on' : 'retain-on-failure',
    launchOptions: process.env.DEMO === '1' ? { slowMo: 800 } : {},
    screenshot: 'only-on-failure',
    // No actionTimeout — let waitForTimeout in while-loop run freely
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
  ],
  tsconfig: './tests/tsconfig.json',
})
