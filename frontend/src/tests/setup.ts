/**
 * Auditex frontend -- Vitest setup.
 * Installs @testing-library/jest-dom matchers and per-test cleanup.
 */
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

// Polyfill URL.createObjectURL for TaskDetail export test
if (typeof URL.createObjectURL === 'undefined') {
  // @ts-expect-error jsdom does not provide createObjectURL by default
  URL.createObjectURL = vi.fn(() => 'blob:mock-url')
}
if (typeof URL.revokeObjectURL === 'undefined') {
  // @ts-expect-error jsdom does not provide revokeObjectURL by default
  URL.revokeObjectURL = vi.fn()
}
