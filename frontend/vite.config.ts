/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/tests/setup.ts'],
    css: false,
    // Exclude Playwright E2E specs from unit runs
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      // Playwright specs live in frontend/tests/ (not src/tests/)
      'tests/**',
    ],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      reportsDirectory: './coverage',
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.d.ts',
        'src/main.tsx',          // Entrypoint — tested via a separate smoke test
        'src/vite-env.d.ts',
        'src/tests/**',
        // The empty hook / child-component directories have no exportable code.
        'src/hooks/**',
        'src/components/AuditTrail/**',
        'src/components/Dashboard/**',
        'src/components/ExportPanel/**',
        'src/components/PoCReport/**',
        'src/components/TaskList/**',
      ],
      thresholds: {
        lines: 100,
        functions: 100,
        branches: 100,
        statements: 100,
      },
    },
  },
})
