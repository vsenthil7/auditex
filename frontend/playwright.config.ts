import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  timeout: 150_000,
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
    actionTimeout: 20_000,
  },
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
  ],
  // Use Playwright's built-in ESM+TS transform (no separate tsc step needed)
  // This avoids the __dirname issue from Vite's bundler moduleResolution
  tsconfig: './tests/tsconfig.json',
})
