/**
 * Smoke test for shared types/index.ts.
 * Types are erased at runtime — we assert the module loads cleanly and any
 * exported runtime constants (none here) are importable.
 */
import { describe, it, expect } from 'vitest'
import * as types from '../types'

describe('types module', () => {
  it('loads without throwing', () => {
    expect(types).toBeDefined()
  })

  it('module has no runtime exports (pure types)', () => {
    // Only type-level symbols are exported. `import * as x` gives us an empty
    // namespace object after TS strips types.
    expect(Object.keys(types)).toEqual([])
  })
})
